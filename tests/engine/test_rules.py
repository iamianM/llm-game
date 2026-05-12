"""Tests for deterministic interaction rules."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.rules import (
    RelationshipDelta,
    apply_action,
    bold_flirt_success_chance,
    flirt_success_chance,
    listen_success_chance,
    talk_success_chance,
)
from src.game.state.models import new_game
from src.game.state.rng import SeededRng


def test_talk_success_chance_uses_banter_and_affection() -> None:
    """A1 TALK math follows the documented starter formula."""
    state = new_game(1)
    chloe = state.islanders[0]

    assert talk_success_chance(state, chloe) == 82


def test_talk_success_adds_affection_when_roll_succeeds() -> None:
    """A successful TALK action applies the affection delta in code."""
    state = new_game(1)
    rng = SeededRng(1)

    result = apply_action(state, PlayerAction(kind=ActionKind.TALK, target_id="chloe"), rng)

    assert result.success is True
    assert result.roll == 18
    assert result.relationship_deltas == {"chloe": RelationshipDelta(affection=2)}
    assert state.islanders[0].relationship.affection == 12


def test_flirt_success_bumps_chemistry() -> None:
    """A successful FLIRT applies chemistry and affection deltas."""
    state = new_game(1)
    rng = SeededRng(1)

    assert flirt_success_chance(state, state.islanders[0]) == 70
    result = apply_action(state, PlayerAction(kind=ActionKind.FLIRT, target_id="chloe"), rng)

    assert result.success is True
    assert result.relationship_deltas == {
        "chloe": RelationshipDelta(affection=2, chemistry=5)
    }
    assert state.islanders[0].relationship.affection == 12
    assert state.islanders[0].relationship.chemistry == 5


def test_flirt_miss_drops_chemistry() -> None:
    """A missed FLIRT lowers chemistry without lowering affection."""
    state = new_game(1)
    state.islanders[0].relationship.chemistry = 5
    rng = SeededRng(5)

    result = apply_action(state, PlayerAction(kind=ActionKind.FLIRT, target_id="chloe"), rng)

    assert result.success is False
    assert result.relationship_deltas == {"chloe": RelationshipDelta(chemistry=-1)}
    assert state.islanders[0].relationship.affection == 10
    assert state.islanders[0].relationship.chemistry == 4


def test_relationship_delta_rejects_unknown_field() -> None:
    """RelationshipDelta catches misspelled stat names."""
    with pytest.raises(ValidationError):
        RelationshipDelta.model_validate({"affection": 1, "chemsitry": 2})


def test_listen_success_adds_trust_and_friendship() -> None:
    """LISTEN uses EQ and applies supportive relationship deltas."""
    state = new_game(1)
    rng = SeededRng(1)

    assert listen_success_chance(state, state.islanders[0]) == 77
    result = apply_action(state, PlayerAction(kind=ActionKind.LISTEN, target_id="chloe"), rng)

    assert result.success is True
    assert result.relationship_deltas == {"chloe": RelationshipDelta(trust=3, friendship=1)}
    assert state.islanders[0].relationship.trust == 3
    assert state.islanders[0].relationship.friendship == 1


def test_bold_flirt_has_higher_reward() -> None:
    """BOLD_FLIRT is higher-risk but higher-reward."""
    state = new_game(1)
    rng = SeededRng(1)

    assert bold_flirt_success_chance(state, state.islanders[0]) == 66
    result = apply_action(state, PlayerAction(kind=ActionKind.BOLD_FLIRT, target_id="chloe"), rng)

    assert result.success is True
    assert result.relationship_deltas == {"chloe": RelationshipDelta(affection=3, chemistry=8)}
