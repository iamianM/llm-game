"""Tests for available action generation and validation."""

from __future__ import annotations

import pytest

from src.game.engine.actions import ActionKind, PlayerAction, available_actions, validate_action
from src.game.state.models import new_game


def test_available_actions_include_visible_conversation_targets_and_advance() -> None:
    """Visible islanders get START_CONVERSATION, plus movement and phase advancement."""
    state = new_game(1)

    actions = [spec.action for spec in available_actions(state)]

    assert PlayerAction(kind=ActionKind.START_CONVERSATION, target_id="chloe") in actions
    assert PlayerAction(kind=ActionKind.START_CONVERSATION, target_id="maya") not in actions
    assert PlayerAction(kind=ActionKind.MOVE, target_id="kitchen") in actions
    assert PlayerAction(kind=ActionKind.MOVE, target_id="terrace") in actions
    assert PlayerAction(kind=ActionKind.ADVANCE_PHASE) in actions
    assert PlayerAction(kind=ActionKind.END_CONVERSATION) in actions


def test_validate_action_rejects_hidden_target() -> None:
    """Targets outside the visible action set fail loudly."""
    state = new_game(1)

    with pytest.raises(ValueError, match="target is not visible"):
        validate_action(
            state,
            PlayerAction(
                kind=ActionKind.START_CONVERSATION,
                target_id="unknown",
                intent_id="friendly_chat_villa",
            ),
        )


def test_validate_action_rejects_other_location_target() -> None:
    """Other-location islanders are not targetable."""
    state = new_game(1)

    with pytest.raises(ValueError, match="target is not visible"):
        validate_action(
            state,
            PlayerAction(
                kind=ActionKind.START_CONVERSATION,
                target_id="maya",
                intent_id="friendly_chat_villa",
            ),
        )
