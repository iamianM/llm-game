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


def test_off_screen_npc_chat_does_not_change_player_relationships() -> None:
    """NPC-NPC events do not mutate relationship-with-player values."""
    state = new_game(7)
    before = [islander.relationship.model_dump() for islander in state.islanders]

    simulate_off_screen(state, SeededRng("phase"))

    after = [islander.relationship.model_dump() for islander in state.islanders]
    assert after == before
