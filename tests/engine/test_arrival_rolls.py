"""Tests for NPC arrival rolls."""

from __future__ import annotations

from src.game.engine.arrival_rolls import interruption_chance, private_chat_chance, roll_arrival
from src.game.engine.conversation import start_conversation
from src.game.engine.memory import add_memory, create_memory
from src.game.state.models import Couple, Location, RelationshipState, new_game
from src.game.state.rng import SeededRng


def test_interruption_chance_includes_chemistry_and_gossip() -> None:
    state = new_game(1)
    maya = state.heartbreakers[1]
    maya.relationship = RelationshipState(chemistry=20)
    add_memory(
        state,
        create_memory(
            holder_id="maya",
            subject_id="liam",
            source="witnessed",
            day=1,
            turn=1,
            weight=7,
            tags=["gossip"],
            content="I saw Liam looking rattled.",
        ),
    )

    assert interruption_chance(state, maya) >= 57


def test_interruption_chance_clamped() -> None:
    state = new_game(1)
    maya = state.heartbreakers[1]
    maya.relationship = RelationshipState(chemistry=100)

    assert interruption_chance(state, maya) == 75


def test_private_chat_chance_subtracts_player_couple_strength() -> None:
    state = new_game(1)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]
    chloe = state.heartbreakers[0]
    chloe.relationship = RelationshipState(affection=80, trust=80, chemistry=20)
    maya = state.heartbreakers[1]
    maya.relationship = RelationshipState(chemistry=20)

    assert private_chat_chance(state, maya, "chloe") < 20


def test_private_chat_chance_clamped() -> None:
    state = new_game(1)
    maya = state.heartbreakers[1]
    maya.relationship = RelationshipState(chemistry=100)

    assert private_chat_chance(state, maya, "chloe") == 60


def test_roll_arrival_records_full_breakdown() -> None:
    state = new_game(1)
    state.heartbreakers[1].location_id = Location.POOL
    start_conversation(state, "chloe", 1)

    result = roll_arrival(state, state.heartbreakers[1], SeededRng(1))

    assert result.arriving_npc_id == "maya"
    assert result.target_id == "chloe"
    assert 5 <= result.interruption_chance <= 75
    assert 3 <= result.private_chat_chance <= 60
    assert 1 <= result.interruption_roll <= 100
    assert 1 <= result.private_chat_roll <= 100
