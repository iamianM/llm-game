"""Tests for available action generation and validation."""

from __future__ import annotations

import pytest

from src.game.engine.actions import ActionKind, PlayerAction, available_actions, validate_action
from src.game.state.models import new_game


def test_available_actions_include_talk_targets_and_advance() -> None:
    """Every visible islander gets TALK, plus phase advancement."""
    state = new_game(1)

    actions = [spec.action for spec in available_actions(state)]

    assert PlayerAction(kind=ActionKind.TALK, target_id="chloe") in actions
    assert PlayerAction(kind=ActionKind.TALK, target_id="maya") in actions
    assert PlayerAction(kind=ActionKind.TALK, target_id="liam") in actions
    assert PlayerAction(kind=ActionKind.ADVANCE_PHASE) in actions


def test_validate_action_rejects_hidden_target() -> None:
    """Targets outside the visible action set fail loudly."""
    state = new_game(1)

    with pytest.raises(ValueError, match="invalid action"):
        validate_action(state, PlayerAction(kind=ActionKind.TALK, target_id="unknown"))
