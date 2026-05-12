"""Tests for deterministic off-screen simulation."""

from __future__ import annotations

from src.game.engine.simulation import simulate_off_screen
from src.game.state.models import new_game
from src.game.state.rng import SeededRng


def test_off_screen_simulation_deterministic_under_replay() -> None:
    """Same state and seed produce the same NPC event sequence."""
    first = new_game(7)
    second = new_game(7)

    first_events = simulate_off_screen(first, SeededRng("phase"))
    second_events = simulate_off_screen(second, SeededRng("phase"))

    assert first_events == second_events
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
