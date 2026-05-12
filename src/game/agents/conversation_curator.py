"""Conversation Curator agent for durable memory commits.

Design sources:
- 07-Gossip-And-Information.md: The Gossip System
- 03-LLM-Architecture.md: Curator-style memory extraction

Implementation rule:
The Curator writes memory content and tags only. The engine assigns ids,
timestamps, and applies the memories to canonical state.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from pathlib import Path

from openai import OpenAI

from src.game.agents.islander_voice import load_dotenv_local
from src.game.state.models import Conversation, GameState, MemoryBatch, MemoryDraft

CONVERSATION_CURATOR_MODEL = "gpt-4.1-mini"

ConversationCuratorFn = Callable[[GameState, Conversation, Sequence[str]], MemoryBatch]


class OpenAIConversationCurator:
    """Memory extraction agent backed by OpenAI Responses."""

    def __init__(self, *, model: str = CONVERSATION_CURATOR_MODEL) -> None:
        load_dotenv_local()
        self._client = OpenAI()
        self._model = model

    def curate(
        self,
        state: GameState,
        conversation: Conversation,
        bystander_ids: Sequence[str] = (),
    ) -> MemoryBatch:
        """Generate a validated memory batch for a closed conversation."""
        response = self._client.responses.parse(
            model=self._model,
            instructions=Path("src/game/agents/prompts/conversation_curator.md").read_text(
                encoding="utf-8"
            ),
            input=_render_context(state, conversation, bystander_ids),
            text_format=MemoryBatch,
            max_output_tokens=900,
        )
        batch = response.output_parsed
        if batch is None:
            raise ValueError("Conversation Curator returned no parsed MemoryBatch")
        validate_memory_batch(batch, state, _participant_ids(conversation), set(bystander_ids))
        return batch


def mock_conversation_curator(
    state: GameState,
    conversation: Conversation,
    bystander_ids: Sequence[str] = (),
) -> MemoryBatch:
    """Return deterministic memory commits for non-LLM tests and fixtures."""
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
    return MemoryBatch(memories=memories)


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


def _render_context(
    state: GameState,
    conversation: Conversation,
    bystander_ids: Sequence[str],
) -> str:
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
            f"Conversation tags: {', '.join(conversation.accumulated_tags) or 'none'}",
            "Exchange history:",
            exchanges or "No exchange history.",
            "Participant relationship states:",
            f"- player toward {target}: tracked by game state",
            f"- {target} toward player: {_relationship_summary(state, conversation.target_id)}",
            "Write the MemoryBatch now.",
        ]
    )


def _participant_ids(conversation: Conversation) -> set[str]:
    return {"player", conversation.target_id}


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
