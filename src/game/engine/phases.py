"""Day and phase progression.

Design sources:
- 08-Daily-Loop.md: Four Phases, Run Length and Pacing
- 10-Elimination-System.md: weekly flow and ceremonies
"""

from src.game.state.models import GameState, Phase

PHASE_ORDER = [
    Phase.MORNING,
    Phase.CHALLENGE,
    Phase.AFTERNOON,
    Phase.TEXT,
    Phase.EVENING,
]

MAX_DAYS = 6


def advance_phase(state: GameState) -> None:
    """Advance the multi-day v0 clock."""
    if state.phase is Phase.COMPLETE:
        return
    if state.phase is Phase.EVENING:
        if state.day >= MAX_DAYS:
            state.phase = Phase.COMPLETE
            return
        state.day += 1
        state.phase = Phase.MORNING
        return
    index = PHASE_ORDER.index(state.phase)
    state.phase = PHASE_ORDER[index + 1]
