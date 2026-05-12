"""Tests for deterministic phase progression."""

from __future__ import annotations

from src.game.engine.phases import advance_phase
from src.game.state.models import Phase, new_game


def test_advance_phase_walks_multi_day_clock() -> None:
    """The day clock advances phases and rolls to the next day."""
    state = new_game(1)

    advance_phase(state)
    assert state.phase is Phase.CHALLENGE
    advance_phase(state)
    assert state.phase is Phase.AFTERNOON
    advance_phase(state)
    assert state.phase is Phase.TEXT
    advance_phase(state)
    assert state.phase is Phase.EVENING
    advance_phase(state)
    assert state.phase is Phase.MORNING
    assert state.day == 2


def test_advance_phase_completes_after_day_six() -> None:
    """The v0 run ends after the sixth evening."""
    state = new_game(1)
    state.day = 6
    state.phase = Phase.EVENING

    advance_phase(state)

    assert state.phase is Phase.COMPLETE
