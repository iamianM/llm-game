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
from src.game.agents.player_autopilot import PolicyDecision
from src.game.agents.villa_orchestrator import EndConversation, NPCSummon, VillaUpdate
from src.game.engine.casa_amor import location_villa, locations_for_villa
from src.game.engine.memory import add_memory_batch
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
    player_autopilot: PolicyDecision | None = None


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
        batch = _apply_summon(state, summon, curate)
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


def normalize_villa_update(state: GameState, update: VillaUpdate) -> VillaUpdate:
    """Make implicit conversation exits explicit before validation."""
    current_locations = {
        islander.id: islander.location_id for islander in state.islanders if not islander.eliminated
    }
    moving_ids = {movement.npc_id for movement in update.npc_movements}
    ended_ids = {ended.conversation_id for ended in update.conversation_ends}
    summoned_ids = {summon.from_conversation_id for summon in update.npc_summoned_elsewhere}
    implied_ends: list[EndConversation] = []
    implied_end_ids: set[str] = set()
    for conversation in state.npc_conversations:
        if conversation.id in ended_ids or conversation.id in summoned_ids:
            continue
        participants = set(conversation.participants)
        participant_moved = bool(moving_ids & participants)
        stale_location = any(
            current_locations.get(participant) != conversation.location_id
            for participant in participants
        )
        if participant_moved or stale_location:
            implied_ends.append(
                EndConversation(conversation_id=conversation.id, reason="participant_moved")
            )
            implied_end_ids.add(conversation.id)
    if not implied_ends:
        return update
    return update.model_copy(
        update={
            "conversation_continues": [
                continuation
                for continuation in update.conversation_continues
                if continuation.conversation_id not in implied_end_ids
            ],
            "conversation_ends": [*update.conversation_ends, *implied_ends],
        }
    )


def validate_villa_update(state: GameState, update: VillaUpdate) -> None:
    if state.pending_gather is not None and any(
        (
            update.npc_movements,
            update.conversation_starts,
            update.conversation_continues,
            update.conversation_ends,
            update.npc_interruptions,
            update.npc_summoned_elsewhere,
        )
    ):
        raise ValueError("villa autonomy is paused while a gather is pending")
    known = {islander.id for islander in state.islanders if not islander.eliminated}
    active_ids = {conversation.id for conversation in state.npc_conversations}
    movement_ids = [movement.npc_id for movement in update.npc_movements]
    if len(movement_ids) != len(set(movement_ids)):
        raise ValueError("duplicate NPC movement in VillaUpdate")
    for movement in update.npc_movements:
        _ensure_known_npc(movement.npc_id, known)
        if movement.target_location not in locations_for_villa(state.villa):
            raise ValueError("NPC movement crosses out of the current villa")
    if len(update.npc_summoned_elsewhere) > 1:
        raise ValueError("at most one NPC summon is allowed per turn")
    for summon in update.npc_summoned_elsewhere:
        _validate_summon(state, summon, known, set(movement_ids))

    ended = {end.conversation_id for end in update.conversation_ends}
    continued = {cont.conversation_id for cont in update.conversation_continues}
    summoned_conversations = {summon.from_conversation_id for summon in update.npc_summoned_elsewhere}
    overlap = ended & continued
    if overlap:
        raise ValueError(f"cannot end and continue same conversation: {sorted(overlap)}")
    summon_overlap = (ended | continued) & summoned_conversations
    if summon_overlap:
        raise ValueError(f"cannot summon from and also end/continue conversation: {sorted(summon_overlap)}")
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
        if start.location not in locations_for_villa(state.villa):
            raise ValueError("NPC conversation start crosses out of the current villa")
        for participant in start.participants:
            _ensure_known_npc(participant, known)
            if location_villa(projected_locations[participant]) is not state.villa:
                raise ValueError(f"NPC conversation participant is not in current villa: {participant}")
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
        if conversation.id in summoned_conversations:
            continue
        for participant in conversation.participants:
            if participant in locked:
                raise ValueError(f"NPC is in player conversation and active NPC chat: {participant}")
            if projected_locations[participant] != conversation.location_id:
                raise ValueError(
                    f"active conversation participant moved away without ending: {conversation.id}"
                )


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


def _validate_summon(
    state: GameState,
    summon: NPCSummon,
    known: set[str],
    moved_ids: set[str],
) -> None:
    _ensure_known_npc(summon.npc_id, known)
    if summon.npc_id in moved_ids:
        raise ValueError("cannot summon and move the same NPC in one VillaUpdate")
    if summon.target_location not in locations_for_villa(state.villa):
        raise ValueError("NPC summon crosses out of the current villa")
    if summon.from_conversation_id == "player_active":
        active = state.active_conversation
        if active is None or active.target_id != summon.npc_id:
            raise ValueError("player_active summon must target the active conversation partner")
        if _islander(state, summon.npc_id).location_id != state.location_id:
            raise ValueError("summoned player conversation target is not at player location")
        return
    conversation = _active_conversation(state, summon.from_conversation_id)
    if summon.npc_id not in conversation.participants:
        raise ValueError("summoned NPC is not in named conversation")
    if _islander(state, summon.npc_id).location_id != conversation.location_id:
        raise ValueError("summoned NPC is not at named conversation location")


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
