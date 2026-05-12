"""Tests for deterministic intent rules."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.intents import get_intent
from src.game.engine.rules import apply_action, intent_success_chance
from src.game.state.models import RelationshipDelta, new_game
from src.game.state.rng import SeededRng


def test_intent_success_chance_uses_configured_stat_and_affection() -> None:
    """F1 intent math uses the intent's configured player stat."""
    state = new_game(1)
    intent = get_intent("friendly_chat_villa")

    assert intent_success_chance(state, state.islanders[0], intent) == 82


def test_friendly_intent_applies_success_delta() -> None:
    """A successful intent applies the configured success delta."""
    state = new_game(1)

    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(1),
    )

    assert result.success is True
    assert result.roll == 18
    assert result.relationship_deltas == {
        "chloe": RelationshipDelta(affection=2, friendship=1)
    }
    assert state.islanders[0].relationship.affection == 12
    assert state.islanders[0].relationship.friendship == 1


def test_locked_intent_fails_loud() -> None:
    """Locked intent ids cannot bypass menu filtering."""
    state = new_game(1)

    with pytest.raises(ValueError, match="locked"):
        apply_action(
            state,
            PlayerAction(
                kind=ActionKind.START_CONVERSATION,
                target_id="chloe",
                intent_id="deep_share_feelings",
            ),
            SeededRng(1),
        )


def test_relationship_delta_rejects_unknown_field() -> None:
    """RelationshipDelta catches misspelled stat names."""
    with pytest.raises(ValidationError):
        RelationshipDelta.model_validate({"affection": 1, "chemsitry": 2})
