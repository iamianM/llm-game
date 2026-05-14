"""Validation and application for Villa Orchestrator commits.

Design sources:
- 09-Social-Dynamics.md: autonomous NPC behavior
- docs/build-plan-G.md: determinism via recorded agent commits

Implementation rule:
The Orchestrator proposes; this module validates and mutates canonical state.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
from typing import cast

from pydantic import BaseModel, ConfigDict, Field

from src.game.agents.background_dialogue import (
    BackgroundDialogueFn,
    BackgroundExchange,
    mock_background_dialogue,
)
from src.game.agents.conversation_curator import (
    ConversationCuratorFn,
    mock_conversation_curator,
)
from src.game.agents.villa_orchestrator import NPCSummon, VillaUpdate
from src.game.engine.memory import add_memory_batch
from src.game.engine.proposals import maybe_form_single_npc_couple_from_conversation
from src.game.engine.villa_validation import normalize_villa_update, validate_villa_update
from src.game.state.autonomy import PendingNPCSummon
from src.game.state.models import (
    BackgroundExchangeRecord,
    Conversation,
    GameState,
    IslanderState,
    Location,
    Memory,
    MemoryBatch,
    NPCNPCConversation,
)
from src.game.state.rng import SeededRng


class AgentCommits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    villa_update: VillaUpdate | None = None
    background_dialogues: list[BackgroundExchange] = Field(default_factory=list)
    curator_batches: list[MemoryBatch] = Field(default_factory=list)


class AppliedVillaChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")

    villa_update: VillaUpdate
    background_dialogues: list[BackgroundExchange] = Field(default_factory=list)
    curator_batches: list[MemoryBatch] = Field(default_factory=list)
    memories: list[Memory] = Field(default_factory=list)


def apply_villa_update(
    state: GameState,
    update: VillaUpdate,
    rng: SeededRng,
    *,
    background_dialogue: BackgroundDialogueFn | None = None,
    conversation_curator: ConversationCuratorFn | None = None,
) -> AppliedVillaChanges:
    return asyncio.run(
        apply_villa_update_async(
            state,
            update,
            rng,
            background_dialogue=background_dialogue,
            conversation_curator=conversation_curator,
        )
    )


async def apply_villa_update_async(
    state: GameState,
    update: VillaUpdate,
    rng: SeededRng,
    *,
    background_dialogue: BackgroundDialogueFn | None = None,
    conversation_curator: ConversationCuratorFn | None = None,
) -> AppliedVillaChanges:
    """Apply a VillaUpdate while batching independent agent calls."""
    update = normalize_villa_update(state, update)
    validate_villa_update(state, update)
    speak = mock_background_dialogue if background_dialogue is None else background_dialogue
    curate = mock_conversation_curator if conversation_curator is None else conversation_curator
    background_dialogues: list[BackgroundExchange] = []
    curator_batches: list[MemoryBatch] = []
    memories: list[Memory] = []

    for movement in update.npc_movements:
        _islander(state, movement.npc_id).location_id = movement.target_location

    for summon in update.npc_summoned_elsewhere:
        batch = await _apply_summon_async(state, summon, curate)
        if batch is not None:
            curator_batches.append(batch)
            memories.extend(add_memory_batch(state, batch, day=state.day, turn=state.turn_index))

    if update.npc_interruptions:
        if state.active_conversation is None:
            raise ValueError("validated interruption missing active conversation")
        state.active_conversation.pending_interruption = update.npc_interruptions[0]

    for start in update.conversation_starts:
        conversation = NPCNPCConversation(
            id=_conversation_id(state, start.participants, start.topic, rng),
            participants=start.participants,
            location_id=start.location,
            topic=start.topic,
            started_on_turn=state.turn_index,
        )
        state.npc_conversations.append(conversation)
        background_dialogues.append(
            await _call_background_dialogue(speak, state, conversation, "")
        )
        _append_background_exchange(state, conversation, background_dialogues[-1])

    continuations = [
        (_active_conversation(state, continuation.conversation_id), continuation.nudge)
        for continuation in update.conversation_continues
    ]
    continuation_exchanges = await asyncio.gather(
        *[
            _call_background_dialogue(speak, state, conversation, nudge)
            for conversation, nudge in continuations
        ]
    )
    for (conversation, _nudge), exchange in zip(continuations, continuation_exchanges, strict=True):
        _append_background_exchange(state, conversation, exchange)
        background_dialogues.append(exchange)

    ended_ids = {ended.conversation_id for ended in update.conversation_ends}
    retained: list[NPCNPCConversation] = []
    conversations_to_curate: list[tuple[NPCNPCConversation, list[str]]] = []
    for conversation in state.npc_conversations:
        if conversation.id not in ended_ids:
            retained.append(conversation)
            continue
        conversation.status = "closed"
        conversations_to_curate.append((conversation, _bystander_ids(state, conversation)))
    state.npc_conversations = retained
    closed_batches = await asyncio.gather(
        *[
            _call_curator(curate, state, conversation, bystanders)
            for conversation, bystanders in conversations_to_curate
        ]
    )
    for batch in closed_batches:
        curator_batches.append(batch)
        memories.extend(add_memory_batch(state, batch, day=state.day, turn=state.turn_index))
    for conversation, _bystanders in conversations_to_curate:
        proposal_batch = maybe_form_single_npc_couple_from_conversation(state, conversation)
        if proposal_batch is None:
            continue
        curator_batches.append(proposal_batch)
        memories.extend(add_memory_batch(state, proposal_batch, day=state.day, turn=state.turn_index))

    return AppliedVillaChanges(
        villa_update=update,
        background_dialogues=background_dialogues,
        curator_batches=curator_batches,
        memories=memories,
    )


async def _call_background_dialogue(
    speak: BackgroundDialogueFn,
    state: GameState,
    conversation: NPCNPCConversation,
    nudge: str,
) -> BackgroundExchange:
    if inspect.iscoroutinefunction(speak):
        return cast(BackgroundExchange, await speak(state, conversation, nudge))
    owner = getattr(speak, "__self__", None)
    async_generate = getattr(owner, "generate_async", None)
    if async_generate is not None:
        return cast(BackgroundExchange, await async_generate(state, conversation, nudge))
    return await asyncio.to_thread(speak, state, conversation, nudge)


async def _call_curator(
    curate: ConversationCuratorFn,
    state: GameState,
    conversation: Conversation | NPCNPCConversation,
    bystanders: list[str],
) -> MemoryBatch:
    if inspect.iscoroutinefunction(curate):
        return cast(MemoryBatch, await curate(state, conversation, bystanders))
    owner = getattr(curate, "__self__", None)
    async_curate = getattr(owner, "curate_async", None)
    if async_curate is not None:
        return cast(MemoryBatch, await async_curate(state, conversation, bystanders))
    return await asyncio.to_thread(curate, state, conversation, bystanders)


def pending_to_summon(pending: PendingNPCSummon) -> NPCSummon:
    return NPCSummon(
        npc_id=pending.npc_id,
        from_conversation_id=pending.from_conversation_id,
        reason=pending.reason,
        target_location=Location(pending.target_location),
    )


def _append_background_exchange(
    state: GameState,
    conversation: NPCNPCConversation,
    exchange: BackgroundExchange,
) -> None:
    first_id, second_id = conversation.participants
    conversation.exchanges.append(
        BackgroundExchangeRecord(
            turn_index=state.turn_index,
            speaker_a_id=first_id,
            speaker_b_id=second_id,
            speaker_a_line=exchange.speaker_a_line,
            speaker_b_line=exchange.speaker_b_line,
            tone=exchange.tone,
        )
    )


def _apply_summon(
    state: GameState,
    summon: NPCSummon,
    curate: ConversationCuratorFn,
) -> MemoryBatch | None:
    if summon.from_conversation_id == "player_active":
        conversation = state.active_conversation
        if conversation is None:
            raise ValueError("player summon missing active conversation")
        conversation.status = "closed"
        batch = curate(state, conversation, _player_conversation_bystanders(state, conversation))
        state.active_conversation = None
    else:
        npc_conversation = _active_conversation(state, summon.from_conversation_id)
        npc_conversation.status = "closed"
        batch = curate(state, npc_conversation, _bystander_ids(state, npc_conversation))
        state.npc_conversations = [
            existing for existing in state.npc_conversations if existing.id != npc_conversation.id
        ]
    _islander(state, summon.npc_id).location_id = summon.target_location
    return batch


async def _apply_summon_async(
    state: GameState,
    summon: NPCSummon,
    curate: ConversationCuratorFn,
) -> MemoryBatch | None:
    if summon.from_conversation_id == "player_active":
        conversation = state.active_conversation
        if conversation is None:
            raise ValueError("player summon missing active conversation")
        conversation.status = "closed"
        batch = await _call_curator(
            curate,
            state,
            conversation,
            _player_conversation_bystanders(state, conversation),
        )
        state.active_conversation = None
    else:
        npc_conversation = _active_conversation(state, summon.from_conversation_id)
        npc_conversation.status = "closed"
        batch = await _call_curator(
            curate,
            state,
            npc_conversation,
            _bystander_ids(state, npc_conversation),
        )
        state.npc_conversations = [
            existing for existing in state.npc_conversations if existing.id != npc_conversation.id
        ]
    _islander(state, summon.npc_id).location_id = summon.target_location
    return batch


def _player_conversation_bystanders(state: GameState, conversation: Conversation) -> list[str]:
    return [
        islander.id
        for islander in state.islanders
        if islander.id != conversation.target_id
        and not islander.eliminated
        and islander.location_id == state.location_id
    ]


def _active_conversation(state: GameState, conversation_id: str) -> NPCNPCConversation:
    for conversation in state.npc_conversations:
        if conversation.id == conversation_id and conversation.status == "active":
            return conversation
    raise ValueError(f"unknown active NPC conversation: {conversation_id}")


def _islander(state: GameState, islander_id: str) -> IslanderState:
    for islander in state.islanders:
        if islander.id == islander_id and not islander.eliminated:
            return islander
    raise ValueError(f"unknown active islander: {islander_id}")


def _bystander_ids(state: GameState, conversation: NPCNPCConversation) -> list[str]:
    bystanders = [
        islander.id
        for islander in state.islanders
        if islander.id not in conversation.participants
        and not islander.eliminated
        and islander.location_id == conversation.location_id
    ]
    if state.location_id == conversation.location_id:
        bystanders.append("player")
    return bystanders


def _conversation_id(
    state: GameState,
    participants: list[str],
    topic: str,
    rng: SeededRng,
) -> str:
    salt = rng.randint(1, 1_000_000)
    raw = "|".join([str(state.day), str(state.turn_index), ",".join(participants), topic, str(salt)])
    return "npcconv_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
