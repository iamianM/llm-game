"""Day and phase progression.

Design sources:
- 08-Daily-Loop.md: Four Phases, Run Length and Pacing
- 10-Elimination-System.md: weekly flow and ceremonies
"""

from src.game.state.models import GameState, Phase
from src.game.state.phase_clock import PhaseClock

PHASE_ORDER = [
    Phase.MORNING,
    Phase.INTROS,
    Phase.CHALLENGE,
    Phase.AFTERNOON,
    Phase.TEXT,
    Phase.EVENING,
]

MAX_DAYS = 6

PHASE_BUDGETS: dict[Phase, int] = {
    Phase.MORNING: 120,
    Phase.INTROS: 180,
    Phase.CHALLENGE: 0,
    Phase.AFTERNOON: 120,
    Phase.TEXT: 30,
    Phase.EVENING: 60,
    Phase.COMPLETE: 0,
}


def advance_phase(state: GameState) -> None:
    """Advance the multi-day v0 clock."""
    state.player.pull_attempts_this_phase = {}
    state.active_ambient_id = None
    state.consecutive_ambient_turns = 0
    if state.phase is Phase.COMPLETE:
        _reset_phase_clock(state)
        return
    if state.phase is Phase.EVENING:
        if state.day >= MAX_DAYS:
            state.phase = Phase.COMPLETE
            _reset_phase_clock(state)
            return
        state.day += 1
        state.phase = Phase.MORNING
        _reset_phase_clock(state)
        return
    if state.phase is Phase.MORNING:
        if state.day == 1 and state.couples and not state.intro_memory_created:
            state.phase = Phase.INTROS
        else:
            state.phase = Phase.CHALLENGE
        _reset_phase_clock(state)
        return
    if state.phase is Phase.INTROS and state.day == 1 and not state.couples:
        # Day-1 intros are the greeting circle that precedes First Spark.
        # Once everyone is met, drop into MORNING so the coupling actions fire.
        state.phase = Phase.MORNING
        _reset_phase_clock(state)
        return
    index = PHASE_ORDER.index(state.phase)
    state.phase = PHASE_ORDER[index + 1]
    _reset_phase_clock(state)


def _reset_phase_clock(state: GameState) -> None:
    state.phase_clock = PhaseClock(
        phase=state.phase.value,
        budget_minutes=PHASE_BUDGETS[state.phase],
    )
