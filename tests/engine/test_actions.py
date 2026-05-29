"""Tests for available action generation and validation."""

from __future__ import annotations

import pytest

from src.game.engine.actions import ActionKind, PlayerAction, available_actions, validate_action
from src.game.state.models import new_game


def test_available_actions_include_visible_conversation_targets_and_ambient() -> None:
    """Visible islanders get categorized START_CONVERSATION openers, movement, and ambient."""
    state = new_game(1)

    actions = [spec.action for spec in available_actions(state)]

    # Free-time openers carry an intent_id so the CharacterMenu category tree
    # populates from real intents. Friendly intents (unlock 0) are always
    # surfaced for a co-located target; nobody who is elsewhere is targetable.
    chloe_starts = [
        action
        for action in actions
        if action.kind is ActionKind.START_CONVERSATION and action.target_id == "chloe"
    ]
    assert chloe_starts, "co-located target should surface conversation openers"
    assert all(action.intent_id is not None for action in chloe_starts)
    assert "friendly_chat_villa" in {action.intent_id for action in chloe_starts}
    assert not any(
        action.kind is ActionKind.START_CONVERSATION and action.target_id == "maya"
        for action in actions
    )
    assert PlayerAction(kind=ActionKind.MOVE, target_id="kitchen") in actions
    assert PlayerAction(kind=ActionKind.MOVE, target_id="terrace") in actions
    assert PlayerAction(kind=ActionKind.AMBIENT, target_id="ambient_wait") in actions
    assert any(action.kind is ActionKind.AMBIENT for action in actions)
    assert PlayerAction(kind=ActionKind.END_CONVERSATION) not in actions


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
