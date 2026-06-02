"""Tests for Private Suite eligibility and rewards."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction, available_actions
from src.game.engine.private_suite import apply_private_suite, private_suite_eligible
from src.game.engine.rules import apply_action
from src.game.engine.turn import run_turn
from src.game.state.models import Couple, Location, Phase, new_game
from src.game.state.rng import SeededRng


def _eligible_state():
    state = new_game(1)
    state.day = 5
    state.phase = Phase.EVENING
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=3)]
    chloe = state.heartbreakers[0]
    chloe.relationship.affection = 80
    chloe.relationship.trust = 60
    return state


def test_private_suite_unlocks_at_couple_strength_70() -> None:
    state = _eligible_state()

    assert private_suite_eligible(state) is True
    assert any(spec.action.kind is ActionKind.PRIVATE_SUITE for spec in available_actions(state))


def test_private_suite_locked_below_threshold() -> None:
    state = _eligible_state()
    state.heartbreakers[0].relationship.trust = 10

    assert private_suite_eligible(state) is False


def test_private_suite_unavailable_before_day_4() -> None:
    state = _eligible_state()
    state.day = 3

    assert private_suite_eligible(state) is False


def test_private_suite_unavailable_in_morning_phase() -> None:
    state = _eligible_state()
    state.phase = Phase.MORNING

    assert private_suite_eligible(state) is False


def test_private_suite_consumable_once_per_run() -> None:
    state = _eligible_state()

    apply_private_suite(state)

    assert private_suite_eligible(state) is False
    assert state.private_suite.used_on_day == 5


def test_private_suite_applies_correct_deltas() -> None:
    state = _eligible_state()

    delta = apply_private_suite(state)

    assert delta.affection == 10
    assert state.heartbreakers[0].relationship.affection == 90
    assert state.heartbreakers[0].relationship.chemistry == 15
    assert state.heartbreakers[0].relationship.trust == 70
    assert state.location_id is Location.PRIVATE_SUITE


def test_private_suite_creates_high_weight_memory_for_both_partners() -> None:
    state = _eligible_state()

    apply_private_suite(state)

    player_memory = [memory for memory in state.player.memories if "private_suite_night" in memory.tags]
    partner_memory = [memory for memory in state.heartbreakers[0].memories if "private_suite_night" in memory.tags]
    assert player_memory[0].emotional_weight == 9
    assert partner_memory[0].emotional_weight == 9


def test_private_suite_intent_kinds_dispatch_correctly() -> None:
    state = _eligible_state()

    result = apply_action(state, PlayerAction(kind=ActionKind.PRIVATE_SUITE), SeededRng(1))

    assert result.success is True
    assert result.relationship_deltas["chloe"].trust == 10


def test_private_suite_turn_records_event_for_narration() -> None:
    state = _eligible_state()

    turn = run_turn(state, PlayerAction(kind=ActionKind.PRIVATE_SUITE), SeededRng(1))

    private_suite_events = [event for event in turn.ceremony_events if event.kind == "private_suite"]
    assert private_suite_events
    assert private_suite_events[0].heartbreaker_id == "chloe"
    assert turn.event_narration is not None
    assert "Chloe" in turn.event_narration.prose
