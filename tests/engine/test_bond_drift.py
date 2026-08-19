"""Tests for overnight bond drift (the resort moving between the player's scenes).

Covers the three drift kinds (consolidation / roving / fade), the soft
ceiling/floor that keep passivity from substituting for real scenes, and the
integration with the phase clock (drift fires exactly once per night, and never
on the final night that rolls straight to COMPLETE).
"""

from __future__ import annotations

from src.game.engine.bond_drift import (
    SOFT_CEIL,
    SOFT_FLOOR,
    apply_overnight_drift,
    plan_drift_for,
)
from src.game.engine.phases import MAX_DAYS, advance_phase
from src.game.state.models import Couple, Phase, new_game


def _couple_with_player(state, heartbreaker_id: str) -> None:
    state.couples.append(
        Couple(partner_a_id=state.player.id, partner_b_id=heartbreaker_id, formed_on_day=1)
    )


def _couple_two_heartbreakers(state, a_id: str, b_id: str) -> None:
    state.couples.append(Couple(partner_a_id=a_id, partner_b_id=b_id, formed_on_day=1))


def _npc(state, heartbreaker_id: str):
    return next(n for n in state.heartbreakers if n.id == heartbreaker_id)


# --- consolidation (coupled with the player) ---------------------------------


def test_consolidation_warms_every_axis() -> None:
    state = new_game(1)
    chloe = _npc(state, "chloe")
    chloe.relationship.affection = 20
    chloe.relationship.chemistry = 20
    chloe.relationship.trust = 20
    chloe.relationship.friendship = 20
    _couple_with_player(state, "chloe")

    drift = plan_drift_for(state, chloe)

    assert drift.kind == "consolidation"
    assert drift.affection == 1
    assert drift.chemistry == 1
    assert drift.trust == 1
    assert drift.friendship == 1


def test_consolidation_never_pushes_past_the_soft_ceiling() -> None:
    state = new_game(1)
    chloe = _npc(state, "chloe")
    # One axis already at the ceiling, one just below it.
    chloe.relationship.affection = SOFT_CEIL
    chloe.relationship.chemistry = SOFT_CEIL - 1
    chloe.relationship.trust = 5
    _couple_with_player(state, "chloe")

    drift = plan_drift_for(state, chloe)

    assert drift.affection == 0  # already at ceiling, no further inflation
    assert drift.chemistry == 1  # steps exactly onto the ceiling
    assert drift.trust == 1


def test_consolidation_leaves_a_scene_built_bond_untouched() -> None:
    state = new_game(1)
    chloe = _npc(state, "chloe")
    # A bond earned well past the passive ceiling must not be cooled by warmth.
    chloe.relationship.affection = 90
    chloe.relationship.chemistry = 90
    chloe.relationship.trust = 90
    chloe.relationship.friendship = 90
    _couple_with_player(state, "chloe")

    drift = plan_drift_for(state, chloe)

    assert drift.is_zero


# --- roving eye (coupled with someone else) ----------------------------------


def test_roving_cools_romance_but_spares_the_platonic_layer() -> None:
    state = new_game(1)
    marcus = _npc(state, "marcus")
    marcus.relationship.affection = 40
    marcus.relationship.chemistry = 40
    marcus.relationship.trust = 40
    marcus.relationship.friendship = 40
    _couple_two_heartbreakers(state, "marcus", "sophie")

    drift = plan_drift_for(state, marcus)

    assert drift.kind == "roving"
    assert drift.affection == -1
    assert drift.chemistry == -2
    assert drift.trust == 0  # mateship lingers
    assert drift.friendship == 0


def test_roving_never_drags_below_the_soft_floor() -> None:
    state = new_game(1)
    marcus = _npc(state, "marcus")
    marcus.relationship.affection = SOFT_FLOOR
    marcus.relationship.chemistry = SOFT_FLOOR + 1
    _couple_two_heartbreakers(state, "marcus", "sophie")

    drift = plan_drift_for(state, marcus)

    assert drift.affection == 0  # already at floor
    assert drift.chemistry == -1  # steps exactly onto the floor, not past it


# --- fade (unpartnered) ------------------------------------------------------


def test_fade_cools_an_unpartnered_heartbreaker() -> None:
    state = new_game(1)
    liam = _npc(state, "liam")
    liam.relationship.affection = 30
    liam.relationship.chemistry = 30
    liam.relationship.trust = 30
    liam.relationship.friendship = 30

    drift = plan_drift_for(state, liam)

    assert drift.kind == "fade"
    assert drift.affection == -1
    assert drift.chemistry == -1
    assert drift.trust == 0
    assert drift.friendship == 0


def test_fade_leaves_an_already_lapsed_bond_alone() -> None:
    state = new_game(1)
    liam = _npc(state, "liam")
    liam.relationship.affection = SOFT_FLOOR
    liam.relationship.chemistry = SOFT_FLOOR

    drift = plan_drift_for(state, liam)

    assert drift.is_zero


# --- apply_overnight_drift over the whole cast -------------------------------


def test_apply_returns_only_heartbreakers_that_actually_moved() -> None:
    state = new_game(1)
    # Park everyone at the floor so fade is a no-op...
    for npc in state.heartbreakers:
        npc.relationship.affection = SOFT_FLOOR
        npc.relationship.chemistry = SOFT_FLOOR
        npc.relationship.trust = SOFT_FLOOR
        npc.relationship.friendship = SOFT_FLOOR
    # ...except one heartbreaker coupled with the player, who consolidates.
    chloe = _npc(state, "chloe")
    chloe.relationship.affection = 20
    _couple_with_player(state, "chloe")

    moved = apply_overnight_drift(state)

    assert [d.heartbreaker_id for d in moved] == ["chloe"]
    assert chloe.relationship.affection == 21


def test_apply_skips_eliminated_heartbreakers() -> None:
    state = new_game(1)
    liam = _npc(state, "liam")
    liam.relationship.affection = 30
    liam.relationship.chemistry = 30
    liam.eliminated = True

    moved = apply_overnight_drift(state)

    assert all(d.heartbreaker_id != "liam" for d in moved)
    assert liam.relationship.affection == 30  # untouched
    assert liam.relationship.chemistry == 30


def test_apply_mutates_bonds_through_the_clamping_chokepoint() -> None:
    state = new_game(1)
    marcus = _npc(state, "marcus")
    marcus.relationship.affection = 40
    marcus.relationship.chemistry = 40
    _couple_two_heartbreakers(state, "marcus", "sophie")

    apply_overnight_drift(state)

    assert marcus.relationship.affection == 39
    assert marcus.relationship.chemistry == 38


# --- phase-clock integration -------------------------------------------------


def test_overnight_rollover_applies_drift_exactly_once() -> None:
    state = new_game(1)
    liam = _npc(state, "liam")
    liam.relationship.affection = 30
    liam.relationship.chemistry = 30
    state.day = 2
    state.phase = Phase.EVENING

    advance_phase(state)

    assert state.day == 3
    assert state.phase is Phase.MORNING
    # Exactly one night of fade: -1 affection / -1 chemistry, not double-applied.
    assert liam.relationship.affection == 29
    assert liam.relationship.chemistry == 29


def test_final_night_rolls_to_complete_without_drift() -> None:
    state = new_game(1)
    liam = _npc(state, "liam")
    liam.relationship.affection = 30
    liam.relationship.chemistry = 30
    state.day = MAX_DAYS
    state.phase = Phase.EVENING

    advance_phase(state)

    assert state.phase is Phase.COMPLETE
    # The resort has wrapped; no overnight drift on a night that never comes.
    assert liam.relationship.affection == 30
    assert liam.relationship.chemistry == 30
