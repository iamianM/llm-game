"""Tests for deterministic phase progression."""

from __future__ import annotations

from src.game.engine.phases import advance_phase
from src.game.state.models import Phase, new_game


def test_advance_phase_walks_a1_day_clock() -> None:
    """The A1 day clock advances without skipping phases."""
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
    assert state.phase is Phase.COMPLETE
    advance_phase(state)
    assert state.phase is Phase.COMPLETE
