"""Tests for player character creation."""

from __future__ import annotations

import pytest

from src.game.engine.character_creation import create_character, reroll_character
from src.game.state.models import CharacterCreation, Gender, PlayerStats, new_game


def test_create_character_assigns_archetype_and_stats() -> None:
    state = new_game(1)
    stats = PlayerStats(charm=9, banter=6, eq=5, graft=5, loyalty=5)

    create_character(state, archetype_id="heartthrob", gender=Gender.MAN, stats=stats)

    assert state.player.archetype_id == "heartthrob"
    assert state.player.gender is Gender.MAN
    assert state.player.stats == stats
    assert state.character_creation is not None
    assert state.character_creation.gender is Gender.MAN


def test_gender_required_in_character_creation() -> None:
    stats = PlayerStats(charm=9, banter=6, eq=5, graft=5, loyalty=5)

    with pytest.raises(ValueError, match="gender"):
        CharacterCreation.model_validate({"archetype_id": "heartthrob", "stats": stats.model_dump()})


def test_create_character_rejects_invalid_total() -> None:
    state = new_game(1)
    stats = PlayerStats(charm=8, banter=6, eq=5, graft=5, loyalty=5)

    with pytest.raises(ValueError, match="exactly 30"):
        create_character(state, archetype_id="heartthrob", gender=Gender.MAN, stats=stats)


def test_create_character_applies_heartthrob_advantage() -> None:
    state = new_game(1)

    create_character(
        state,
        archetype_id="heartthrob",
        gender=Gender.MAN,
        stats=PlayerStats(charm=9, banter=6, eq=5, graft=5, loyalty=5),
    )

    assert state.islanders[0].relationship.chemistry == 5


def test_create_character_applies_class_clown_advantage() -> None:
    state = new_game(1)

    create_character(
        state,
        archetype_id="class_clown",
        gender=Gender.MAN,
        stats=PlayerStats(charm=5, banter=9, eq=6, graft=5, loyalty=5),
    )

    assert state.player.public_perception == 60


def test_create_character_applies_loyal_friend_advantage() -> None:
    state = new_game(1)

    create_character(
        state,
        archetype_id="loyal_friend",
        gender=Gender.MAN,
        stats=PlayerStats(charm=5, banter=6, eq=5, graft=5, loyalty=9),
    )

    assert all(islander.relationship.friendship == 5 for islander in state.islanders)


def test_reroll_rejected_after_use() -> None:
    state = new_game(1)

    reroll_character(state)

    with pytest.raises(ValueError, match="already"):
        reroll_character(state)
