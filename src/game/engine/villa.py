"""Validation and application for Villa Orchestrator commits.

Design sources:
- 09-Social-Dynamics.md: autonomous NPC behavior
- docs/build-plan-G.md: determinism via recorded agent commits

Implementation rule:
The Orchestrator proposes; this module validates and mutates canonical state.
"""

from __future__ import annotations

import hashlib

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
from src.game.agents.villa_orchestrator import VillaUpdate
from src.game.engine.memory import add_memory_batch
from src.game.state.models import (
    BackgroundExchangeRecord,
    GameState,
    IslanderState,
    Memory,
    MemoryBatch,
    NPCNPCConversation,
)
from src.game.state.rng import SeededRng


class AgentCommits(BaseModel):
    """Agent commits produced or replayed during one turn."""

    model_config = ConfigDict(extra="forbid")

    villa_update: VillaUpdate | None = None
    background_dialogues: list[BackgroundExchange] = Field(default_factory=list)
    curator_batches: list[MemoryBatch] = Field(default_factory=list)


class AppliedVillaChanges(BaseModel):
    """State changes applied from one VillaUpdate."""

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
    """Validate and apply one Orchestrator update."""
    validate_villa_update(state, update)
    speak = mock_background_dialogue if background_dialogue is None else background_dialogue
    curate = mock_conversation_curator if conversation_curator is None else conversation_curator
    background_dialogues: list[BackgroundExchange] = []
    curator_batches: list[MemoryBatch] = []
    memories: list[Memory] = []

    for movement in update.npc_movements:
        _islander(state, movement.npc_id).location_id = movement.target_location

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
        exchange = speak(state, conversation, "")
        _append_background_exchange(state, conversation, exchange)
        background_dialogues.append(exchange)
        state.npc_conversations.append(conversation)

    for continuation in update.conversation_continues:
        conversation = _active_conversation(state, continuation.conversation_id)
        exchange = speak(state, conversation, continuation.nudge)
        _append_background_exchange(state, conversation, exchange)
        background_dialogues.append(exchange)

    ended_ids = {ended.conversation_id for ended in update.conversation_ends}
    retained: list[NPCNPCConversation] = []
    for conversation in state.npc_conversations:
        if conversation.id not in ended_ids:
            retained.append(conversation)
            continue
        conversation.status = "closed"
        batch = curate(state, conversation, _bystander_ids(state, conversation))
        curator_batches.append(batch)
        memories.extend(add_memory_batch(state, batch, day=state.day, turn=state.turn_index))
    state.npc_conversations = retained

    return AppliedVillaChanges(
        villa_update=update,
        background_dialogues=background_dialogues,
        curator_batches=curator_batches,
        memories=memories,
    )


def validate_villa_update(state: GameState, update: VillaUpdate) -> None:
    """Fail loud if a VillaUpdate cannot be applied to current state."""
    known = {islander.id for islander in state.islanders if not islander.eliminated}
    active_ids = {conversation.id for conversation in state.npc_conversations}
    movement_ids = [movement.npc_id for movement in update.npc_movements]
    if len(movement_ids) != len(set(movement_ids)):
        raise ValueError("duplicate NPC movement in VillaUpdate")
    for movement in update.npc_movements:
        _ensure_known_npc(movement.npc_id, known)

    ended = {end.conversation_id for end in update.conversation_ends}
    continued = {cont.conversation_id for cont in update.conversation_continues}
    overlap = ended & continued
    if overlap:
        raise ValueError(f"cannot end and continue same conversation: {sorted(overlap)}")
    for conversation_id in ended | continued:
        if conversation_id not in active_ids:
            raise ValueError(f"unknown active NPC conversation: {conversation_id}")

    projected_locations = {
        islander.id: islander.location_id for islander in state.islanders if not islander.eliminated
    }
    for movement in update.npc_movements:
        projected_locations[movement.npc_id] = movement.target_location

    if len(update.npc_interruptions) > 1:
        raise ValueError("at most one NPC interruption is allowed per turn")
    if update.npc_interruptions:
        active = state.active_conversation
        if active is None:
            raise ValueError("cannot interrupt when player has no active conversation")
        if active.pending_interruption is not None:
            raise ValueError("cannot interrupt while another interruption is already pending")
        interruption = update.npc_interruptions[0]
        _ensure_known_npc(interruption.interrupter_id, known)
        if interruption.interrupter_id == active.target_id:
            raise ValueError("conversation partner cannot interrupt their own conversation")
        if projected_locations[interruption.interrupter_id] != state.location_id:
            raise ValueError("interrupter is not at player location")

    locked = _player_locked_npc_ids(state)
    used_in_new: set[str] = set()
    for start in update.conversation_starts:
        if len(set(start.participants)) != 2:
            raise ValueError(f"conversation start requires two unique participants: {start}")
        for participant in start.participants:
            _ensure_known_npc(participant, known)
            if participant in locked:
                raise ValueError(f"NPC is in player conversation and cannot start NPC chat: {participant}")
            if participant in used_in_new:
                raise ValueError(f"NPC appears in multiple new conversations: {participant}")
            used_in_new.add(participant)
            if projected_locations[participant] != start.location:
                raise ValueError(f"conversation start participant not at location: {start}")

    for conversation in state.npc_conversations:
        if conversation.id in ended:
            continue
        for participant in conversation.participants:
            if participant in locked:
                raise ValueError(f"NPC is in player conversation and active NPC chat: {participant}")
            if projected_locations[participant] != conversation.location_id:
                raise ValueError(
                    f"active conversation participant moved away without ending: {conversation.id}"
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


def _ensure_known_npc(npc_id: str, known: set[str]) -> None:
    if npc_id == "player":
        raise ValueError("player cannot appear in NPC-NPC villa update")
    if npc_id not in known:
        raise ValueError(f"unknown or eliminated NPC in VillaUpdate: {npc_id}")


def _player_locked_npc_ids(state: GameState) -> set[str]:
    if state.active_conversation is None:
        return set()
    return {state.active_conversation.target_id}


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
