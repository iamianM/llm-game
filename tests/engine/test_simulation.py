"""Tests for deterministic off-screen simulation."""

from __future__ import annotations

from src.game.engine.simulation import simulate_off_screen
from src.game.state.models import Location, new_game
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


def test_off_screen_chat_creates_memories_for_both() -> None:
    """NPC-NPC events create memories for both participants."""
    state = new_game(7)
    for islander in state.islanders:
        islander.location_id = Location.POOL

    events = simulate_off_screen(state, SeededRng(20))

    social = [event for event in events if event.target_id is not None]
    assert social
    assert any(memory.subject_id == "maya" for memory in state.islanders[0].memories)
    assert any(memory.subject_id == "chloe" for memory in state.islanders[1].memories)


def test_drama_events_have_high_weight() -> None:
    """High mutual rolls create gossip-eligible drama memories."""
    state = new_game(7)
    for islander in state.islanders:
        islander.location_id = Location.POOL

    events = simulate_off_screen(state, SeededRng(20))

    assert any(event.kind == "drama" for event in events)
    assert any(
        memory.emotional_weight >= 7 and "drama" in memory.tags
        for islander in state.islanders
        for memory in islander.memories
    )


def test_npcs_move_toward_chemistry_partners() -> None:
    """High player chemistry can pull an NPC toward the player's location."""
    state = new_game(7)
    state.location_id = Location.POOL
    state.islanders[0].location_id = Location.KITCHEN
    state.islanders[0].relationship.chemistry = 100

    simulate_off_screen(state, SeededRng(1))

    assert state.islanders[0].location_id is Location.POOL
