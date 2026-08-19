"""Conversation Curator agent for durable memory commits.

Design sources:
- docs/design/07-Gossip-And-Information.md: The Gossip System
- docs/design/03-LLM-Architecture.md: Curator-style memory extraction

Implementation rule:
The Curator writes memory content and tags only. The engine assigns ids,
timestamps, and applies the memories to canonical state.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from functools import cached_property
from pathlib import Path

from openai import OpenAI

from src.game.agents.heartbreaker_voice import load_dotenv_local
from src.game.agents.runtime import (
    GAME_AGENT_MODEL,
    AgentGenerationError,
    AgentValidationError,
    begin_agent_attempt,
    build_game_client,
    end_agent_attempt,
    mark_agent_trace_validation_error,
    reasoning_request_kwargs,
    record_agent_trace,
)
from src.game.state.models import (
    Conversation,
    GameState,
    Gender,
    MemoryBatch,
    MemoryDraft,
    NPCNPCConversation,
)

CONVERSATION_CURATOR_MODEL = GAME_AGENT_MODEL
CONVERSATION_CURATOR_PROMPT = "src/game/agents/prompts/conversation_curator.md"
_CONVERSATION_CURATOR_PROMPT_FILE = Path(__file__).parent / "prompts" / "conversation_curator.md"

CuratableConversation = Conversation | NPCNPCConversation
ConversationCuratorFn = Callable[[GameState, CuratableConversation, Sequence[str]], MemoryBatch]


class OpenAIConversationCurator:
    """Memory extraction agent backed by OpenAI Responses."""

    def __init__(self, *, model: str = CONVERSATION_CURATOR_MODEL) -> None:
        load_dotenv_local()
        self._model = model

    @cached_property
    def _client(self) -> OpenAI:
        return build_game_client()

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
            attempt_number = attempt + 1
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
            attempt_token = begin_agent_attempt(attempt_number)
            try:
                try:
                    batch = self._generate_batch(retry_context)
                except Exception as exc:
                    mark_agent_trace_validation_error("conversation_curator", attempt_number, exc)
                    last_error = ValueError(str(exc))
                    if attempt == 2:
                        raise AgentGenerationError(str(exc)) from exc
                    continue
            finally:
                end_agent_attempt(attempt_token)
            try:
                validate_memory_batch(batch, state, participant_ids, bystander_set)
                return batch
            except ValueError as exc:
                mark_agent_trace_validation_error("conversation_curator", attempt_number, exc)
                last_error = exc
                if attempt == 2:
                    raise AgentValidationError(str(exc)) from exc
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
            instructions=_CONVERSATION_CURATOR_PROMPT_FILE.read_text(encoding="utf-8"),
            input=rendered_context,
            text_format=MemoryBatch,
            **reasoning_request_kwargs(),
        )
        batch = response.output_parsed
        record_agent_trace(
            agent_name="conversation_curator",
            model=self._model,
            prompt_path=CONVERSATION_CURATOR_PROMPT,
            response=response,
            output=batch,
        )
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
        kind="player",
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
    valid_ids = {"player", *(heartbreaker.id for heartbreaker in state.heartbreakers)}
    holders = {memory.holder_id for memory in batch.memories}
    missing_participants = participant_ids - holders
    if missing_participants:
        raise ValueError(f"curator omitted participant memories: {sorted(missing_participants)}")
    for memory in batch.memories:
        if memory.holder_id not in valid_ids:
            raise ValueError(f"unknown memory holder_id: {memory.holder_id}")
        if memory.subject_id not in valid_ids and memory.subject_id != "resort":
            raise ValueError(f"unknown memory subject_id: {memory.subject_id}")
        if memory.source == "direct" and memory.holder_id not in participant_ids:
            raise ValueError(f"direct memory holder was not a participant: {memory.holder_id}")
        if memory.source == "witnessed" and memory.holder_id not in bystander_ids:
            raise ValueError(f"witnessed memory holder was not a bystander: {memory.holder_id}")
        if not memory.tags:
            raise ValueError(f"memory has no tags: {memory}")
    for seed in batch.gossip_seeds:
        if seed.holder_id not in valid_ids:
            raise ValueError(f"unknown gossip seed holder_id: {seed.holder_id}")
        if seed.subject_id not in valid_ids and seed.subject_id != "resort":
            raise ValueError(f"unknown gossip seed subject_id: {seed.subject_id}")


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
            "Pronouns (use exactly these — never guess gender from a name):",
            _pronoun_line(state, "player"),
            _pronoun_line(state, conversation.target_id),
            f"Bystanders: {_list_ids(bystander_ids)}",
            f"Required direct memory holders: player, {conversation.target_id}",
            "Memory holder checklist:",
            "- holder_id: player",
            f"- holder_id: {conversation.target_id}",
            f"Valid subject ids: {_valid_subject_ids(state)}",
            f"Mentioned third-party ids: {_mentioned_third_party_ids(state, conversation)}",
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
                tags=["background", "witnessed", "gossip"],
            )
        )
    return MemoryBatch(
        kind="background",
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
            "Pronouns (use exactly these — never guess gender from a name):",
            _pronoun_line(state, first_id),
            _pronoun_line(state, second_id),
            f"Topic: {conversation.topic}",
            f"Bystanders: {_list_ids(bystander_ids)}",
            f"Required direct memory holders: {first_id}, {second_id}",
            "Memory holder checklist:",
            f"- holder_id: {first_id}",
            f"- holder_id: {second_id}",
            f"Valid subject ids: {_valid_subject_ids(state)}",
            f"Mentioned third-party ids: {_mentioned_third_party_ids(state, conversation)}",
            "Exchange history:",
            exchanges or "No exchange history.",
            "Participant relationship states:",
            f"- {first_id}: {_relationship_summary(state, first_id)}",
            f"- {second_id}: {_relationship_summary(state, second_id)}",
            "Write the MemoryBatch now.",
        ]
    )


def _relationship_summary(state: GameState, heartbreaker_id: str) -> str:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == heartbreaker_id:
            rel = heartbreaker.relationship
            return (
                f"affection {rel.affection}, chemistry {rel.chemistry}, "
                f"trust {rel.trust}, friendship {rel.friendship}"
            )
    return "unknown"


def _name_for(state: GameState, holder_id: str) -> str:
    if holder_id == "player":
        return state.player.name
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == holder_id:
            return heartbreaker.name
    return holder_id


def _pronouns_for_gender(gender: Gender) -> str:
    return "she/her" if gender == Gender.WOMAN else "he/him"


def _gender_for(state: GameState, holder_id: str) -> Gender | None:
    if holder_id == "player":
        return state.player.gender
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == holder_id:
            return heartbreaker.gender
    return None


def _pronoun_line(state: GameState, holder_id: str) -> str:
    """`id: Name (he/him)` so the curator never guesses gender from a name."""
    name = _name_for(state, holder_id)
    gender = _gender_for(state, holder_id)
    if gender is None:
        return f"- {holder_id}: {name}"
    return f"- {holder_id}: {name} ({_pronouns_for_gender(gender)})"


def _list_ids(ids: Sequence[str]) -> str:
    return ", ".join(ids) if ids else "none"


def _valid_subject_ids(state: GameState) -> str:
    ids = ["player", "resort", *(heartbreaker.id for heartbreaker in state.heartbreakers if not heartbreaker.eliminated)]
    return ", ".join(ids)


def _mentioned_third_party_ids(state: GameState, conversation: CuratableConversation) -> str:
    participant_ids = _participant_ids(conversation)
    mentioned = []
    text = _conversation_text(conversation).lower()
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id in participant_ids or heartbreaker.eliminated:
            continue
        if heartbreaker.name.lower() in text:
            mentioned.append(f"{heartbreaker.id} ({heartbreaker.name}, {_pronouns_for_gender(heartbreaker.gender)})")
    return ", ".join(mentioned) if mentioned else "none"


def _conversation_text(conversation: CuratableConversation) -> str:
    if isinstance(conversation, NPCNPCConversation):
        return " ".join(
            f"{exchange.speaker_a_line} {exchange.speaker_b_line}"
            for exchange in conversation.exchanges
        )
    return " ".join(
        f"{exchange.player_dialogue} {exchange.npc_dialogue}"
        for exchange in conversation.exchanges
    )
