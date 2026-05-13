"""Per-phase time budget helpers."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.phases import PHASE_BUDGETS
from src.game.state.models import GameState
from src.game.state.phase_clock import PhaseClock

ACTION_TIME_COST: dict[ActionKind, int] = {
    ActionKind.CREATE_CHARACTER: 0,
    ActionKind.START_CONVERSATION: 20,
    ActionKind.RESPOND_WITH: 5,
    ActionKind.END_CONVERSATION: 0,
    ActionKind.CHALLENGE_RESPONSE: 0,
    ActionKind.HIDEAWAY: 60,
    ActionKind.CASA_DECISION: 10,
    ActionKind.MOVE: 5,
    ActionKind.RECOUPLE: 0,
    ActionKind.ADVANCE_PHASE: 0,
}


def ensure_phase_clock(state: GameState) -> None:
    """Repair old or mismatched clocks at phase boundaries."""
    if state.phase_clock.phase != state.phase.value:
        state.phase_clock = PhaseClock(
            phase=state.phase.value,
            budget_minutes=PHASE_BUDGETS[state.phase],
        )


def action_time_cost(action: PlayerAction) -> int:
    return ACTION_TIME_COST[action.kind]


def deduct_time(state: GameState, action: PlayerAction) -> int:
    """Apply an action's fixed time cost to the current phase clock."""
    ensure_phase_clock(state)
    cost = action_time_cost(action)
    state.phase_clock.elapsed_minutes += cost
    return cost


def check_auto_advance(state: GameState) -> bool:
    """Return whether the current phase clock has expired."""
    ensure_phase_clock(state)
    return state.phase_clock.expired
