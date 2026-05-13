"""Tests for Hideaway eligibility and rewards."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction, available_actions
from src.game.engine.hideaway import apply_hideaway, hideaway_eligible
from src.game.engine.rules import apply_action
from src.game.state.models import Couple, Location, Phase, new_game
from src.game.state.rng import SeededRng


def _eligible_state():
    state = new_game(1)
    state.day = 5
    state.phase = Phase.EVENING
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=3)]
    chloe = state.islanders[0]
    chloe.relationship.affection = 80
    chloe.relationship.trust = 60
    return state


def test_hideaway_unlocks_at_couple_strength_70() -> None:
    state = _eligible_state()

    assert hideaway_eligible(state) is True
    assert any(spec.action.kind is ActionKind.HIDEAWAY for spec in available_actions(state))


def test_hideaway_locked_below_threshold() -> None:
    state = _eligible_state()
    state.islanders[0].relationship.trust = 10

    assert hideaway_eligible(state) is False


def test_hideaway_unavailable_before_day_4() -> None:
    state = _eligible_state()
    state.day = 3

    assert hideaway_eligible(state) is False


def test_hideaway_unavailable_in_morning_phase() -> None:
    state = _eligible_state()
    state.phase = Phase.MORNING

    assert hideaway_eligible(state) is False


def test_hideaway_consumable_once_per_run() -> None:
    state = _eligible_state()

    apply_hideaway(state)

    assert hideaway_eligible(state) is False
    assert state.hideaway.used_on_day == 5


def test_hideaway_applies_correct_deltas() -> None:
    state = _eligible_state()

    delta = apply_hideaway(state)

    assert delta.affection == 10
    assert state.islanders[0].relationship.affection == 90
    assert state.islanders[0].relationship.chemistry == 15
    assert state.islanders[0].relationship.trust == 70
    assert state.location_id is Location.HIDEAWAY


def test_hideaway_creates_high_weight_memory_for_both_partners() -> None:
    state = _eligible_state()

    apply_hideaway(state)

    player_memory = [memory for memory in state.player.memories if "hideaway_night" in memory.tags]
    partner_memory = [memory for memory in state.islanders[0].memories if "hideaway_night" in memory.tags]
    assert player_memory[0].emotional_weight == 9
    assert partner_memory[0].emotional_weight == 9


def test_hideaway_intent_kinds_dispatch_correctly() -> None:
    state = _eligible_state()

    result = apply_action(state, PlayerAction(kind=ActionKind.HIDEAWAY), SeededRng(1))

    assert result.success is True
    assert result.relationship_deltas["chloe"].trust == 10
