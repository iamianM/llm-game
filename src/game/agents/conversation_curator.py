"""Conversation Curator agent for durable memory commits.

Design sources:
- 07-Gossip-And-Information.md: The Gossip System
- 03-LLM-Architecture.md: Curator-style memory extraction

Implementation rule:
The Curator writes memory content and tags only. The engine assigns ids,
timestamps, and applies the memories to canonical state.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable, Sequence
from functools import cached_property
from pathlib import Path

from openai import OpenAI

from src.game.agents.islander_voice import load_dotenv_local
from src.game.state.models import (
    Conversation,
    GameState,
    MemoryBatch,
    MemoryDraft,
    NPCNPCConversation,
)

CONVERSATION_CURATOR_MODEL = "gpt-5.4-mini"

CuratableConversation = Conversation | NPCNPCConversation
ConversationCuratorFn = Callable[[GameState, CuratableConversation, Sequence[str]], MemoryBatch]


class OpenAIConversationCurator:
    """Memory extraction agent backed by OpenAI Responses."""

    def __init__(self, *, model: str = CONVERSATION_CURATOR_MODEL) -> None:
        load_dotenv_local()
        self._model = model

    @cached_property
    def _client(self) -> OpenAI:
        return OpenAI()

    def curate(
        self,
        state: GameState,
        conversation: CuratableConversation,
        bystander_ids: Sequence[str] = (),
    ) -> MemoryBatch:
        """Generate a validated memory batch for a closed conversation."""
        rendered = _render_context(state, conversation, bystander_ids)
        participant_ids = _participant_ids(conversation)
        bystander_set = set(bystander_ids)
        last_error: ValueError | None = None
        for attempt in range(3):
            retry_context = rendered
            if last_error is not None:
                required_holders = ", ".join(sorted(participant_ids))
                retry_context = (
                    f"{rendered}\n\n"
                    "The previous MemoryBatch failed validation. "
                    f"Validation error: {last_error}. "
                    "Return a corrected MemoryBatch using exact ids from the context, "
                    "not display names. "
                    f"You must include at least one direct memory for each participant holder: {required_holders}."
                )
            batch = self._generate_batch(retry_context)
            try:
                validate_memory_batch(batch, state, participant_ids, bystander_set)
                return batch
            except ValueError as exc:
                last_error = exc
                if attempt == 2:
                    raise
        raise AssertionError("unreachable curator retry state")

    async def curate_async(
        self,
        state: GameState,
        conversation: CuratableConversation,
        bystander_ids: Sequence[str] = (),
    ) -> MemoryBatch:
        """Curate a closed conversation without blocking sibling curator calls."""
        return await asyncio.to_thread(self.curate, state, conversation, bystander_ids)

    def _generate_batch(self, rendered_context: str) -> MemoryBatch:
        """Request one parsed memory batch from the model."""
        response = self._client.responses.parse(
            model=self._model,
            reasoning={"effort": "low"},
            instructions=Path("src/game/agents/prompts/conversation_curator.md").read_text(
                encoding="utf-8"
            ),
            input=rendered_context,
            text_format=MemoryBatch,
            max_output_tokens=900,
        )
        batch = response.output_parsed
        if batch is None:
            raise ValueError("Conversation Curator returned no parsed MemoryBatch")
        return batch


def mock_conversation_curator(
    state: GameState,
    conversation: CuratableConversation,
    bystander_ids: Sequence[str] = (),
) -> MemoryBatch:
    """Return deterministic memory commits for non-LLM tests and fixtures."""
    if isinstance(conversation, NPCNPCConversation):
        return _mock_npc_conversation_memory(state, conversation, bystander_ids)
    target_id = conversation.target_id
    target_name = _name_for(state, target_id)
    tag = conversation.accumulated_tags[0] if conversation.accumulated_tags else "private"
    memories = [
        MemoryDraft(
            holder_id="player",
            subject_id=target_id,
            content=f"I remember how {target_name} reacted when our {tag} chat shifted.",
            source="direct",
            emotional_weight=5,
            tags=[tag, "player_conversation"],
        ),
        MemoryDraft(
            holder_id=target_id,
            subject_id="player",
            content=f"I remember the player making our {tag} chat feel personal.",
            source="direct",
            emotional_weight=5,
            tags=[tag, "player_conversation"],
        ),
    ]
    for bystander_id in bystander_ids:
        memories.append(
            MemoryDraft(
                holder_id=bystander_id,
                subject_id=target_id,
                content=f"I noticed {target_name} looked different after talking with the player.",
                source="witnessed",
                emotional_weight=4,
                tags=[tag, "witnessed"],
            )
        )
    return MemoryBatch(
        memories=memories,
        summary=f"Player and {target_name} closed a {tag} conversation with a clear emotional shift.",
        gossip_seeds=[],
    )


def validate_memory_batch(
    batch: MemoryBatch,
    state: GameState,
    participant_ids: set[str],
    bystander_ids: set[str],
) -> None:
    """Fail loud when a memory commit violates the curator contract."""
    valid_ids = {"player", *(islander.id for islander in state.islanders)}
    holders = {memory.holder_id for memory in batch.memories}
    missing_participants = participant_ids - holders
    if missing_participants:
        raise ValueError(f"curator omitted participant memories: {sorted(missing_participants)}")
    for memory in batch.memories:
        if memory.holder_id not in valid_ids:
            raise ValueError(f"unknown memory holder_id: {memory.holder_id}")
        if memory.subject_id not in valid_ids and memory.subject_id != "villa":
            raise ValueError(f"unknown memory subject_id: {memory.subject_id}")
        if memory.source == "direct" and memory.holder_id not in participant_ids:
            raise ValueError(f"direct memory holder was not a participant: {memory.holder_id}")
        if memory.source == "witnessed" and memory.holder_id not in bystander_ids:
            raise ValueError(f"witnessed memory holder was not a bystander: {memory.holder_id}")
        if re.search(r"\d", memory.content):
            raise ValueError(f"memory content contains digits: {memory.content!r}")
        if not memory.tags:
            raise ValueError(f"memory has no tags: {memory}")
    if batch.summary and re.search(r"\d", batch.summary):
        raise ValueError(f"summary contains digits: {batch.summary!r}")
    for seed in batch.gossip_seeds:
        if seed.holder_id not in valid_ids:
            raise ValueError(f"unknown gossip seed holder_id: {seed.holder_id}")
        if seed.subject_id not in valid_ids and seed.subject_id != "villa":
            raise ValueError(f"unknown gossip seed subject_id: {seed.subject_id}")
        if re.search(r"\d", seed.gist):
            raise ValueError(f"gossip seed contains digits: {seed.gist!r}")


def _render_context(
    state: GameState,
    conversation: CuratableConversation,
    bystander_ids: Sequence[str],
) -> str:
    if isinstance(conversation, NPCNPCConversation):
        return _render_npc_context(state, conversation, bystander_ids)
    target = _name_for(state, conversation.target_id)
    exchanges = "\n".join(
        (
            f"- intent {exchange.intent_id}; success {exchange.success}; "
            f"player said {exchange.player_dialogue!r}; NPC said {exchange.npc_dialogue!r}; "
            f"tone {exchange.npc_tone}; tags {', '.join(exchange.tags)}"
        )
        for exchange in conversation.exchanges
    )
    return "\n".join(
        [
            f"Day: {state.day}",
            f"Location: {state.location_id.value}",
            f"Participants: player, {conversation.target_id} ({target})",
            f"Bystanders: {_list_ids(bystander_ids)}",
            f"Required direct memory holders: player, {conversation.target_id}",
            f"Conversation tags: {', '.join(conversation.accumulated_tags) or 'none'}",
            "Exchange history:",
            exchanges or "No exchange history.",
            "Participant relationship states:",
            f"- player toward {target}: tracked by game state",
            f"- {target} toward player: {_relationship_summary(state, conversation.target_id)}",
            "Write the MemoryBatch now.",
        ]
    )


def _participant_ids(conversation: CuratableConversation) -> set[str]:
    if isinstance(conversation, NPCNPCConversation):
        return set(conversation.participants)
    return {"player", conversation.target_id}


def _mock_npc_conversation_memory(
    state: GameState,
    conversation: NPCNPCConversation,
    bystander_ids: Sequence[str],
) -> MemoryBatch:
    first_id, second_id = conversation.participants
    first_name = _name_for(state, first_id)
    second_name = _name_for(state, second_id)
    memories = [
        MemoryDraft(
            holder_id=first_id,
            subject_id=second_id,
            content=f"I remember {second_name} leaning into our chat about {conversation.topic}.",
            source="direct",
            emotional_weight=5,
            tags=["background", "npc_conversation"],
        ),
        MemoryDraft(
            holder_id=second_id,
            subject_id=first_id,
            content=f"I remember {first_name} having a real point about {conversation.topic}.",
            source="direct",
            emotional_weight=5,
            tags=["background", "npc_conversation"],
        ),
    ]
    for bystander_id in bystander_ids:
        memories.append(
            MemoryDraft(
                holder_id=bystander_id,
                subject_id=first_id,
                content=f"I noticed {first_name} and {second_name} looked wrapped up in each other.",
                source="witnessed",
                emotional_weight=4,
                tags=["background", "witnessed"],
            )
        )
    return MemoryBatch(
        memories=memories,
        summary=f"{first_name} and {second_name} talked about {conversation.topic}.",
        gossip_seeds=[],
    )


def _render_npc_context(
    state: GameState,
    conversation: NPCNPCConversation,
    bystander_ids: Sequence[str],
) -> str:
    first_id, second_id = conversation.participants
    exchanges = "\n".join(
        (
            f"- {exchange.speaker_a_id}: {exchange.speaker_a_line!r}; "
            f"{exchange.speaker_b_id}: {exchange.speaker_b_line!r}; tone {exchange.tone}"
        )
        for exchange in conversation.exchanges
    )
    return "\n".join(
        [
            f"Day: {state.day}",
            f"Location: {conversation.location_id.value}",
            f"Participants: {first_id} ({_name_for(state, first_id)}), "
            f"{second_id} ({_name_for(state, second_id)})",
            f"Topic: {conversation.topic}",
            f"Bystanders: {_list_ids(bystander_ids)}",
            f"Required direct memory holders: {first_id}, {second_id}",
            "Exchange history:",
            exchanges or "No exchange history.",
            "Participant relationship states:",
            f"- {first_id}: {_relationship_summary(state, first_id)}",
            f"- {second_id}: {_relationship_summary(state, second_id)}",
            "Write the MemoryBatch now.",
        ]
    )


def _relationship_summary(state: GameState, islander_id: str) -> str:
    for islander in state.islanders:
        if islander.id == islander_id:
            rel = islander.relationship
            return (
                f"affection {rel.affection}, chemistry {rel.chemistry}, "
                f"trust {rel.trust}, friendship {rel.friendship}"
            )
    return "unknown"


def _name_for(state: GameState, holder_id: str) -> str:
    if holder_id == "player":
        return state.player.name
    for islander in state.islanders:
        if islander.id == holder_id:
            return islander.name
    return holder_id


def _list_ids(ids: Sequence[str]) -> str:
    return ", ".join(ids) if ids else "none"
