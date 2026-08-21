"""Resort autonomy helpers used by the turn pipeline."""

from __future__ import annotations

import asyncio

from src.game.agents.background_dialogue import BackgroundDialogueFn
from src.game.agents.conversation_curator import ConversationCuratorFn
from src.game.agents.resort_orchestrator import (
    NPCMovement,
    ResortOrchestratorFn,
    ResortUpdate,
)
from src.game.agents.runtime import AgentValidationError
from src.game.engine.arrival_rolls import ArrivalRoll, roll_arrival
from src.game.engine.peer import advance_peer_attractions, maybe_form_peer_couples
from src.game.engine.phases import is_finale_evening
from src.game.engine.resort import (
    AppliedResortChanges,
    apply_resort_update_async,
    pending_to_summon,
)
from src.game.engine.resort_validation import normalize_resort_update, validate_resort_update
from src.game.state.autonomy import PendingNPCSummon
from src.game.state.models import GameState, HeartbreakerState, Location, NPCInterruption
from src.game.state.rng import SeededRng


def apply_resort_turn(
    state: GameState,
    rng: SeededRng,
    resort_orchestrator: ResortOrchestratorFn,
    *,
    background_dialogue: BackgroundDialogueFn,
    conversation_curator: ConversationCuratorFn,
) -> tuple[ResortUpdate, AppliedResortChanges, list[ArrivalRoll]]:
    return asyncio.run(
        apply_resort_turn_async(
            state,
            rng,
            resort_orchestrator,
            background_dialogue=background_dialogue,
            conversation_curator=conversation_curator,
        )
    )


async def apply_resort_turn_async(
    state: GameState,
    rng: SeededRng,
    resort_orchestrator: ResortOrchestratorFn,
    *,
    background_dialogue: BackgroundDialogueFn,
    conversation_curator: ConversationCuratorFn,
) -> tuple[ResortUpdate, AppliedResortChanges, list[ArrivalRoll]]:
    """Apply one orchestrator turn with parallel background agents."""
    if state.pending_gather is not None:
        resort_update = ResortUpdate()
        return resort_update, AppliedResortChanges(resort_update=resort_update), []
    # Intros are a tight scripted meet-and-greet — the cast watches the
    # player work the room, so there's no value in firing the orchestrator
    # (background NPC movements / new NPC-NPC chats) per intro turn. Skip
    # it during INTROS to cut ~10-15s of LLM latency per intro.
    from src.game.state.models import Phase

    if state.phase is Phase.INTROS:
        resort_update = ResortUpdate()
        return resort_update, AppliedResortChanges(resort_update=resort_update), []
    base_update = _orchestrate(state, resort_orchestrator)
    resort_update = _merge_pending_summon(state, base_update)
    if resort_update is not base_update:
        # _merge_pending_summon spliced in a pending summon. The base update and
        # the summon are each valid alone, but together they can conflict — e.g.
        # the orchestrator validly moved the active partner this turn while the
        # summon also summons that same partner away ("cannot summon and move the
        # same NPC"). That clash would otherwise surface inside
        # apply_resort_update_async and dead-screen the turn, so re-validate the
        # combined update and fall back to the already-valid base (skip the
        # summon this turn) if it no longer holds.
        try:
            validate_resort_update(state, resort_update)
        except ValueError:
            resort_update = base_update
    pre_locations = {
        heartbreaker.id: heartbreaker.location_id for heartbreaker in state.heartbreakers
    }
    resort_changes = await apply_resort_update_async(
        state,
        resort_update,
        rng,
        background_dialogue=background_dialogue,
        conversation_curator=conversation_curator,
    )
    # The resort has its own love stories: heartbreakers grow attracted to each other
    # as they spend time co-located, and single pairs who click hard enough
    # couple up off-screen. Both feed the gossip mill + morning recap. Run after
    # the orchestrator's movements land so attraction reflects this turn's
    # positions.
    peer_memories = advance_peer_attractions(state, rng.fork("peer-advance"))
    peer_memories.extend(maybe_form_peer_couples(state, rng.fork("peer-couple")))
    resort_changes.memories.extend(peer_memories)
    arrival_rolls = _roll_arrivals_for_movements(
        state, resort_update.npc_movements, pre_locations, rng
    )
    return resort_update, resort_changes, arrival_rolls


def _orchestrate(state: GameState, orchestrate: ResortOrchestratorFn) -> ResortUpdate:
    """Normalize and validate the configured orchestrator's proposal."""
    update = normalize_resort_update(state, orchestrate(state))
    try:
        validate_resort_update(state, update)
    except ValueError as exc:
        raise AgentValidationError(str(exc)) from exc
    return update


def _merge_pending_summon(state: GameState, resort_update: ResortUpdate) -> ResortUpdate:
    pending = state.pending_npc_summon
    if pending is None or resort_update.npc_summoned_elsewhere:
        return resort_update
    if not _pending_summon_still_valid(state, pending):
        state.pending_npc_summon = None
        return resort_update
    state.pending_npc_summon = None
    return resort_update.model_copy(update={"npc_summoned_elsewhere": [pending_to_summon(pending)]})


def _pending_summon_still_valid(state: GameState, pending: PendingNPCSummon) -> bool:
    if pending.from_conversation_id == "player_active":
        return (
            state.active_conversation is not None
            and state.active_conversation.target_id == pending.npc_id
        )
    return any(
        conversation.id == pending.from_conversation_id
        and conversation.status == "active"
        and pending.npc_id in conversation.participants
        for conversation in state.npc_conversations
    )


def _roll_arrivals_for_movements(
    state: GameState,
    movements: list[NPCMovement],
    pre_locations: dict[str, Location],
    rng: SeededRng,
) -> list[ArrivalRoll]:
    if state.active_conversation is None:
        return []
    rolls: list[ArrivalRoll] = []
    for movement in movements:
        if movement.target_location != state.location_id:
            continue
        if pre_locations.get(movement.npc_id) == state.location_id:
            continue
        if movement.npc_id == state.active_conversation.target_id:
            continue
        arriving = _find_heartbreaker(state, movement.npc_id)
        roll = roll_arrival(state, arriving, rng.fork(f"arrival-{movement.npc_id}"))
        rolls.append(roll)
        _apply_arrival_roll(state, roll, arriving)
    return rolls


def _apply_arrival_roll(state: GameState, roll: ArrivalRoll, arriving: HeartbreakerState) -> None:
    active = state.active_conversation
    if active is None:
        return
    if (
        roll.interruption_hit
        and active.pending_interruption is None
        and not is_finale_evening(state)
    ):
        active.pending_interruption = NPCInterruption(
            interrupter_id=roll.arriving_npc_id,
            reason="has_gossip" if _recent_high_weight_memories(arriving) else "jealous",
            urgency="insistent" if roll.interruption_chance >= 50 else "polite",
        )
    if roll.private_chat_hit and state.pending_npc_summon is None:
        state.pending_npc_summon = PendingNPCSummon(
            npc_id=active.target_id,
            from_conversation_id="player_active",
            reason="chemistry_partner_arrived",
            target_location=arriving.location_id.value,
        )


def _recent_high_weight_memories(heartbreaker: HeartbreakerState) -> bool:
    return any(memory.emotional_weight >= 5 for memory in heartbreaker.memories[-5:])


def _find_heartbreaker(state: GameState, heartbreaker_id: str) -> HeartbreakerState:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == heartbreaker_id and not heartbreaker.eliminated:
            return heartbreaker
    raise ValueError(f"unknown heartbreaker: {heartbreaker_id}")
