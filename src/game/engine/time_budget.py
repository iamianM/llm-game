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
    ActionKind.PRIVATE_SUITE: 60,
    ActionKind.FLUSH_DECISION: 10,
    ActionKind.JOIN_GATHER: 30,
    ActionKind.AMBIENT: 20,
    ActionKind.INTRODUCE_TO: 25,
    ActionKind.MOVE: 5,
    ActionKind.PAIR: 0,
    ActionKind.PROPOSE_PAIR: 20,
    ActionKind.NPC_PROPOSAL_RESPONSE: 10,
}


def ensure_phase_clock(state: GameState) -> None:
    """Repair old or mismatched clocks at phase boundaries."""
    if state.phase_clock.phase != state.phase.value:
        state.phase_clock = PhaseClock(
            phase=state.phase.value,
            budget_minutes=PHASE_BUDGETS[state.phase],
        )


def action_time_cost(action: PlayerAction, state: GameState | None = None) -> int:
    if action.kind is ActionKind.AMBIENT and action.target_id == "ambient_wait" and state is not None:
        return state.phase_clock.remaining
    if action.kind is ActionKind.AMBIENT and state is not None:
        return 5 if state.active_ambient_id == action.target_id else 20
    return ACTION_TIME_COST[action.kind]


def deduct_time(state: GameState, action: PlayerAction) -> int:
    """Apply an action's fixed time cost to the current phase clock."""
    ensure_phase_clock(state)
    cost = action_time_cost(action, state)
    state.phase_clock.elapsed_minutes += cost
    return cost


def check_auto_advance(state: GameState) -> bool:
    """Return whether the current phase clock has expired.

    Holds the auto-advance while a round-based minigame is mid-round —
    otherwise the phase header flips from "Challenge" to "Afternoon"
    while the player is still answering the quiz, which reads as broken.
    """
    ensure_phase_clock(state)
    if not state.phase_clock.expired:
        return False
    if (
        state.pending_challenge is not None
        and state.pending_challenge.result is None
        and state.pending_challenge.current_round_index < len(state.pending_challenge.rounds)
    ):
        return False
    return True
