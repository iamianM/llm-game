"""Validation helpers for Villa Orchestrator commits."""

from __future__ import annotations

from src.game.agents.villa_orchestrator import EndConversation, NPCSummon, VillaUpdate
from src.game.engine.casa_amor import location_villa, locations_for_villa
from src.game.state.models import GameState, Location, NPCNPCConversation


def normalize_villa_update(state: GameState, update: VillaUpdate) -> VillaUpdate:
    """Repair near-miss NPC ids, then make implicit conversation exits explicit."""
    update = _resolve_npc_ids(state, update)
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


def _resolve_npc_ids(state: GameState, update: VillaUpdate) -> VillaUpdate:
    """Repair near-miss NPC ids (e.g. bare ``jordan`` -> canonical ``jordan_start``).

    The Orchestrator model occasionally emits an islander's display name or a
    suffix-stripped id instead of the canonical id it was handed in context. A
    single such slip would otherwise dead-screen the whole turn via
    ``_ensure_known_npc``. Map every recoverable token back to its canonical id
    before validation; leave genuinely unknown tokens untouched so validation
    still rejects them clearly.
    """
    active = [islander for islander in state.islanders if not islander.eliminated]
    known_ids = {islander.id for islander in active}

    def resolve(token: str) -> str:
        return _canonical_npc_id(token, active, known_ids)

    changed = False
    movements = []
    for movement in update.npc_movements:
        resolved = resolve(movement.npc_id)
        if resolved != movement.npc_id:
            changed = True
            movement = movement.model_copy(update={"npc_id": resolved})
        movements.append(movement)

    starts = []
    for start in update.conversation_starts:
        participants = [resolve(participant) for participant in start.participants]
        if participants != list(start.participants):
            changed = True
            start = start.model_copy(update={"participants": participants})
        starts.append(start)

    interruptions = []
    for interruption in update.npc_interruptions:
        resolved = resolve(interruption.interrupter_id)
        if resolved != interruption.interrupter_id:
            changed = True
            interruption = interruption.model_copy(update={"interrupter_id": resolved})
        interruptions.append(interruption)

    summons = []
    for summon in update.npc_summoned_elsewhere:
        resolved = resolve(summon.npc_id)
        if resolved != summon.npc_id:
            changed = True
            summon = summon.model_copy(update={"npc_id": resolved})
        summons.append(summon)

    if not changed:
        return update
    return update.model_copy(
        update={
            "npc_movements": movements,
            "conversation_starts": starts,
            "npc_interruptions": interruptions,
            "npc_summoned_elsewhere": summons,
        }
    )


def _canonical_npc_id(token: str, active: list, known_ids: set[str]) -> str:
    """Best-effort map a possibly-near-miss token to a canonical active id.

    Precedence: exact id, case-insensitive id, display name, leading id segment
    (``jordan`` -> ``jordan_start``), then first-name token. ``player`` and any
    truly unknown token are returned unchanged so validation rejects them.
    """
    if token in known_ids:
        return token
    lowered = token.strip().lower()
    if not lowered:
        return token
    for islander in active:
        if islander.id.lower() == lowered:
            return islander.id
    for islander in active:
        if islander.name.lower() == lowered:
            return islander.id
    for islander in active:
        if islander.id.lower().split("_", 1)[0] == lowered:
            return islander.id
    for islander in active:
        if islander.name.lower().split(" ", 1)[0] == lowered:
            return islander.id
    return token


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
        if _islander_location(state, summon.npc_id) != state.location_id:
            raise ValueError("summoned player conversation target is not at player location")
        return
    conversation = _active_conversation(state, summon.from_conversation_id)
    if summon.npc_id not in conversation.participants:
        raise ValueError("summoned NPC is not in named conversation")
    if _islander_location(state, summon.npc_id) != conversation.location_id:
        raise ValueError("summoned NPC is not at named conversation location")


def _active_conversation(state: GameState, conversation_id: str) -> NPCNPCConversation:
    for conversation in state.npc_conversations:
        if conversation.id == conversation_id and conversation.status == "active":
            return conversation
    raise ValueError(f"unknown active NPC conversation: {conversation_id}")


def _islander_location(state: GameState, islander_id: str) -> Location:
    for islander in state.islanders:
        if islander.id == islander_id and not islander.eliminated:
            return islander.location_id
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
