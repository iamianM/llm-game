"""Villa autonomy helpers used by the turn pipeline."""

from __future__ import annotations

import asyncio

from src.game.agents.background_dialogue import BackgroundDialogueFn
from src.game.agents.conversation_curator import ConversationCuratorFn
from src.game.agents.villa_orchestrator import (
    NPCMovement,
    VillaOrchestratorFn,
    VillaUpdate,
    mock_villa_orchestrator,
)
from src.game.engine.arrival_rolls import ArrivalRoll, roll_arrival
from src.game.engine.villa import (
    AppliedVillaChanges,
    apply_villa_update_async,
    pending_to_summon,
)
from src.game.engine.villa_validation import normalize_villa_update, validate_villa_update
from src.game.state.autonomy import PendingNPCSummon
from src.game.state.models import GameState, IslanderState, Location, NPCInterruption
from src.game.state.rng import SeededRng


def apply_villa_turn(
    state: GameState,
    rng: SeededRng,
    villa_orchestrator: VillaOrchestratorFn | None,
    *,
    background_dialogue: BackgroundDialogueFn | None,
    conversation_curator: ConversationCuratorFn | None,
) -> tuple[VillaUpdate, AppliedVillaChanges, list[ArrivalRoll]]:
    return asyncio.run(
        apply_villa_turn_async(
            state,
            rng,
            villa_orchestrator,
            background_dialogue=background_dialogue,
            conversation_curator=conversation_curator,
        )
    )


async def apply_villa_turn_async(
    state: GameState,
    rng: SeededRng,
    villa_orchestrator: VillaOrchestratorFn | None,
    *,
    background_dialogue: BackgroundDialogueFn | None,
    conversation_curator: ConversationCuratorFn | None,
) -> tuple[VillaUpdate, AppliedVillaChanges, list[ArrivalRoll]]:
    """Apply one orchestrator turn with parallel background agents."""
    if state.pending_gather is not None:
        villa_update = VillaUpdate()
        return villa_update, AppliedVillaChanges(villa_update=villa_update), []
    # Intros are a tight scripted meet-and-greet — the cast watches the
    # player work the room, so there's no value in firing the orchestrator
    # (background NPC movements / new NPC-NPC chats) per intro turn. Skip
    # it during INTROS to cut ~10-15s of LLM latency per intro.
    from src.game.state.models import Phase
    if state.phase is Phase.INTROS:
        villa_update = VillaUpdate()
        return villa_update, AppliedVillaChanges(villa_update=villa_update), []
    orchestrate = mock_villa_orchestrator if villa_orchestrator is None else villa_orchestrator
    base_update = _safe_orchestrate(state, orchestrate)
    villa_update = _merge_pending_summon(state, base_update)
    if villa_update is not base_update:
        # _merge_pending_summon spliced in a pending summon. The base update and
        # the summon are each valid alone, but together they can conflict — e.g.
        # the orchestrator validly moved the active partner this turn while the
        # summon also pulls that same partner away ("cannot summon and move the
        # same NPC"). That clash would otherwise surface inside
        # apply_villa_update_async and dead-screen the turn, so re-validate the
        # combined update and fall back to the already-valid base (skip the
        # summon this turn) if it no longer holds.
        try:
            validate_villa_update(state, villa_update)
        except Exception:
            villa_update = base_update
    pre_locations = {islander.id: islander.location_id for islander in state.islanders}
    villa_changes = await apply_villa_update_async(
        state,
        villa_update,
        rng,
        background_dialogue=background_dialogue,
        conversation_curator=conversation_curator,
    )
    arrival_rolls = _roll_arrivals_for_movements(state, villa_update.npc_movements, pre_locations, rng)
    return villa_update, villa_changes, arrival_rolls


def _safe_orchestrate(state: GameState, orchestrate: VillaOrchestratorFn) -> VillaUpdate:
    """Run the villa orchestrator without ever dead-screening the player's turn.

    The orchestrator only drives *ambient* flavor — background NPC movement and
    NPC-NPC chatter. The live agent retries on validation failure and then
    raises (every failed attempt is already recorded in the agent trace). A raise
    propagating up here would crash the whole turn and discard the player's
    actual exchange, so on any failure — the agent giving up, or an update that
    still fails validation even after near-miss id repair — we degrade to an
    empty update. The villa simply holds still for one turn instead of throwing a
    dead screen. Validating here (before the summon is merged in) also keeps a
    pending summon intact even when the LLM's own movement/chatter is unusable.
    """
    try:
        update = orchestrate(state)
        update = normalize_villa_update(state, update)
        validate_villa_update(state, update)
        return update
    except Exception:
        return VillaUpdate()


def _merge_pending_summon(state: GameState, villa_update: VillaUpdate) -> VillaUpdate:
    pending = state.pending_npc_summon
    if pending is None or villa_update.npc_summoned_elsewhere:
        return villa_update
    if not _pending_summon_still_valid(state, pending):
        state.pending_npc_summon = None
        return villa_update
    state.pending_npc_summon = None
    return villa_update.model_copy(update={"npc_summoned_elsewhere": [pending_to_summon(pending)]})


def _pending_summon_still_valid(state: GameState, pending: PendingNPCSummon) -> bool:
    if pending.from_conversation_id == "player_active":
        return state.active_conversation is not None and state.active_conversation.target_id == pending.npc_id
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
        arriving = _find_islander(state, movement.npc_id)
        roll = roll_arrival(state, arriving, rng.fork(f"arrival-{movement.npc_id}"))
        rolls.append(roll)
        _apply_arrival_roll(state, roll, arriving)
    return rolls


def _apply_arrival_roll(state: GameState, roll: ArrivalRoll, arriving: IslanderState) -> None:
    active = state.active_conversation
    if active is None:
        return
    if roll.interruption_hit and active.pending_interruption is None:
        active.pending_interruption = NPCInterruption(
            interrupter_id=roll.arriving_npc_id,
            reason="has_gossip" if _recent_high_weight_memories(arriving) else "jealous",
            urgency="insistent" if roll.interruption_chance >= 50 else "polite",
        )
    if roll.pull_hit and state.pending_npc_summon is None:
        state.pending_npc_summon = PendingNPCSummon(
            npc_id=active.target_id,
            from_conversation_id="player_active",
            reason="chemistry_partner_arrived",
            target_location=arriving.location_id.value,
        )


def _recent_high_weight_memories(islander: IslanderState) -> bool:
    return any(memory.emotional_weight >= 5 for memory in islander.memories[-5:])


def _find_islander(state: GameState, islander_id: str) -> IslanderState:
    for islander in state.islanders:
        if islander.id == islander_id and not islander.eliminated:
            return islander
    raise ValueError(f"unknown islander: {islander_id}")
