"""Tests for deterministic interaction rules."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.rules import apply_action, talk_success_chance
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
    assert result.relationship_deltas == {"chloe": {"affection": 2}}
    assert state.islanders[0].relationship.affection == 12
