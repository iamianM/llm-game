"""Tests for phase time budgets."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.phases import PHASE_BUDGETS, advance_phase
from src.game.engine.time_budget import action_time_cost, check_auto_advance, deduct_time
from src.game.engine.turn import run_turn
from src.game.state.models import Phase, new_game
from src.game.state.rng import SeededRng


def test_action_time_costs_match_phase_budget_contract() -> None:
    assert action_time_cost(PlayerAction(kind=ActionKind.START_CONVERSATION)) == 20
    assert action_time_cost(PlayerAction(kind=ActionKind.RESPOND_WITH)) == 5
    assert action_time_cost(PlayerAction(kind=ActionKind.MOVE, target_id="kitchen")) == 5
    assert action_time_cost(PlayerAction(kind=ActionKind.HIDEAWAY)) == 60
    assert action_time_cost(PlayerAction(kind=ActionKind.ADVANCE_PHASE)) == 0


def test_deduct_time_marks_clock_expired() -> None:
    state = new_game(1)
    state.phase_clock.elapsed_minutes = 115

    cost = deduct_time(state, PlayerAction(kind=ActionKind.MOVE, target_id="kitchen"))

    assert cost == 5
    assert state.phase_clock.remaining == 0
    assert check_auto_advance(state) is True


def test_advance_phase_resets_phase_clock_budget() -> None:
    state = new_game(1)
    state.phase_clock.elapsed_minutes = 120

    advance_phase(state)

    assert state.phase is Phase.CHALLENGE
    assert state.phase_clock.phase == Phase.CHALLENGE.value
    assert state.phase_clock.budget_minutes == PHASE_BUDGETS[Phase.CHALLENGE]
    assert state.phase_clock.elapsed_minutes == 0


def test_run_turn_auto_advances_when_budget_expires() -> None:
    state = new_game(1)
    rng = SeededRng(1)
    result = None

    for _ in range(6):
        result = run_turn(
            state,
            PlayerAction(
                kind=ActionKind.START_CONVERSATION,
                target_id="chloe",
                intent_id="friendly_chat_villa",
            ),
            rng,
        )

    assert result is not None
    assert result.auto_advance is True
    assert result.time_cost == 20
    assert state.phase is Phase.CHALLENGE
    assert state.phase_clock.phase == Phase.CHALLENGE.value
    assert state.phase_clock.elapsed_minutes == 0
