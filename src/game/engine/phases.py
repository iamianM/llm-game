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
    Phase.COMPLETE,
]


def advance_phase(state: GameState) -> None:
    """Advance the one-day Phase A1 clock."""
    if state.phase is Phase.COMPLETE:
        return
    index = PHASE_ORDER.index(state.phase)
    state.phase = PHASE_ORDER[index + 1]
