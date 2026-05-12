"""Tests for available action generation and validation."""

from __future__ import annotations

import pytest

from src.game.engine.actions import ActionKind, PlayerAction, available_actions, validate_action
from src.game.state.models import PlayerStats, new_game


def test_available_actions_include_talk_targets_and_advance() -> None:
    """Visible islanders get social actions, plus movement and phase advancement."""
    state = new_game(1)

    actions = [spec.action for spec in available_actions(state)]

    assert PlayerAction(kind=ActionKind.TALK, target_id="chloe") in actions
    assert PlayerAction(kind=ActionKind.FLIRT, target_id="chloe") in actions
    assert PlayerAction(kind=ActionKind.BOLD_FLIRT, target_id="chloe") in actions
    assert PlayerAction(kind=ActionKind.LISTEN, target_id="chloe") in actions
    assert PlayerAction(kind=ActionKind.TALK, target_id="maya") not in actions
    assert PlayerAction(kind=ActionKind.MOVE, target_id="kitchen") in actions
    assert PlayerAction(kind=ActionKind.MOVE, target_id="terrace") in actions
    assert PlayerAction(kind=ActionKind.ADVANCE_PHASE) in actions
    assert PlayerAction(kind=ActionKind.LEAVE) in actions


def test_validate_action_rejects_hidden_target() -> None:
    """Targets outside the visible action set fail loudly."""
    state = new_game(1)

    with pytest.raises(ValueError, match="invalid action"):
        validate_action(state, PlayerAction(kind=ActionKind.TALK, target_id="unknown"))


def test_validate_action_rejects_other_location_target() -> None:
    """Other-location islanders are not targetable."""
    state = new_game(1)

    with pytest.raises(ValueError, match="invalid action"):
        validate_action(state, PlayerAction(kind=ActionKind.TALK, target_id="maya"))


def test_bold_flirt_locked_below_graft_5() -> None:
    """Bold flirt is hidden when the stat gate is not met."""
    state = new_game(1, player_stats=PlayerStats(charm=7, banter=7, eq=7, graft=3, loyalty=6))

    actions = [spec.action for spec in available_actions(state)]

    assert PlayerAction(kind=ActionKind.BOLD_FLIRT, target_id="chloe") not in actions


def test_bold_flirt_unlocked_at_graft_5() -> None:
    """Bold flirt appears once the stat gate is met."""
    state = new_game(1, player_stats=PlayerStats(charm=7, banter=7, eq=6, graft=5, loyalty=5))

    actions = [spec.action for spec in available_actions(state)]

    assert PlayerAction(kind=ActionKind.BOLD_FLIRT, target_id="chloe") in actions
