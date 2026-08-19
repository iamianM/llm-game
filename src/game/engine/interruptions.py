"""NPC interruption response mechanics."""

from __future__ import annotations

from src.game.engine.actions import PlayerAction
from src.game.engine.flush_of_hearts import locations_for_resort
from src.game.engine.memory import add_memory, create_memory
from src.game.engine.results import ChanceBreakdown, ForcedMovement, MechanicalResult
from src.game.engine.state_access import apply_relationship_delta, find_heartbreaker
from src.game.state.models import GameState, Location, RelationshipDelta
from src.game.state.rng import SeededRng

INTERRUPTION_INTENT_KINDS = {
    "accept_interruption",
    "defer_interruption",
    "ignore_interruption",
}


def defer_chance(state: GameState, interrupter_id: str) -> int:
    """Return the chance that a polite deferral lands well."""
    return defer_chance_breakdown(state, interrupter_id).final_chance


def defer_chance_breakdown(state: GameState, interrupter_id: str) -> ChanceBreakdown:
    """Return an auditable chance that a polite deferral lands well."""
    interrupter = find_heartbreaker(state, interrupter_id)
    stat = state.player.stats.eq
    stat_contribution = stat * 4
    affection_contribution = interrupter.relationship.affection // 4
    pre_cap = 50 + stat_contribution + affection_contribution
    return ChanceBreakdown(
        kind="interruption_defer",
        base=50,
        stat_name="eq",
        stat_value=stat,
        stat_multiplier=4,
        stat_contribution=stat_contribution,
        affection_value=interrupter.relationship.affection,
        affection_divisor=4,
        affection_contribution=affection_contribution,
        pre_cap=pre_cap,
        cap=90,
        floor=10,
        final_chance=max(10, min(90, pre_cap)),
    )


def apply_interruption_response(
    state: GameState,
    action: PlayerAction,
    rng: SeededRng,
) -> MechanicalResult:
    """Apply one of the code-owned interruption response options."""
    conversation = state.active_conversation
    if conversation is None or conversation.pending_interruption is None:
        raise ValueError("interruption response requires a pending interruption")
    interruption = conversation.pending_interruption
    current = find_heartbreaker(state, conversation.target_id)
    interrupter = find_heartbreaker(state, interruption.interrupter_id)
    intent_id = action.intent_id
    deltas: dict[str, RelationshipDelta] = {}
    roll: int | None = None
    chance: int | None = None
    breakdown: ChanceBreakdown | None = None
    forced_movements: list[ForcedMovement] = []
    success = True
    tags = ["interruption", str(intent_id), interruption.reason, interruption.urgency]

    if intent_id == "accept_interruption":
        current_delta = RelationshipDelta(affection=-2)
        interrupter_delta = RelationshipDelta(affection=3)
        apply_relationship_delta(current, current_delta)
        apply_relationship_delta(interrupter, interrupter_delta)
        deltas = {current.id: current_delta, interrupter.id: interrupter_delta}
    elif intent_id == "defer_interruption":
        breakdown = defer_chance_breakdown(state, interrupter.id)
        chance = breakdown.final_chance
        roll = rng.randint(1, 100)
        success = roll <= chance
        interrupter_delta = RelationshipDelta(affection=-1 if success else -3)
        apply_relationship_delta(interrupter, interrupter_delta)
        deltas = {interrupter.id: interrupter_delta}
        if not success:
            remember_interruption_snub(state, interrupter.id, "snubbed_publicly", 7)
    elif intent_id == "ignore_interruption":
        interrupter_delta = RelationshipDelta(affection=-4)
        apply_relationship_delta(interrupter, interrupter_delta)
        deltas = {interrupter.id: interrupter_delta}
        remember_interruption_snub(state, interrupter.id, "ignored_in_public", 8)
        target_location = _walkaway_location(state, interrupter.id, rng)
        interrupter.location_id = target_location
        forced_movements.append(
            ForcedMovement(
                actor_id=interrupter.id,
                kind="walks_away_after_snub",
                target_location=target_location,
            )
        )
    else:
        raise ValueError(f"unknown interruption response: {intent_id}")

    conversation.pending_interruption = None
    return MechanicalResult(
        action=action.model_copy(update={"target_id": interrupter.id}),
        success=success,
        roll=roll,
        success_chance=chance,
        chance_breakdown=breakdown if chance is not None else None,
        relationship_deltas=deltas,
        tags=tags,
        forced_movements=forced_movements,
    )


def remember_interruption_snub(
    state: GameState,
    interrupter_id: str,
    tag: str,
    weight: int,
) -> None:
    """Create direct and witnessed memories after a poor interruption response."""
    add_memory(
        state,
        create_memory(
            holder_id=interrupter_id,
            subject_id="player",
            source="direct",
            day=state.day,
            turn=state.turn_index,
            weight=weight,
            tags=["interruption", tag],
            content=f"I remember the player leaving me feeling {tag.replace('_', ' ')}.",
        ),
    )
    for heartbreaker in state.heartbreakers:
        if (
            heartbreaker.id != interrupter_id
            and not heartbreaker.eliminated
            and heartbreaker.location_id == state.location_id
        ):
            add_memory(
                state,
                create_memory(
                    holder_id=heartbreaker.id,
                    subject_id="player",
                    source="witnessed",
                    day=state.day,
                    turn=state.turn_index,
                    weight=max(4, weight - 2),
                    tags=["interruption", tag, "witnessed"],
                    content=(
                        "I saw the player handle an interruption and leave someone "
                        f"{tag.replace('_', ' ')}."
                    ),
                ),
            )


def _walkaway_location(state: GameState, interrupter_id: str, rng: SeededRng) -> Location:
    interrupter = find_heartbreaker(state, interrupter_id)
    candidates = [
        location
        for location in sorted(locations_for_resort(state.resort), key=lambda item: item.value)
        if location != interrupter.location_id
    ]
    return rng.choice(candidates)
