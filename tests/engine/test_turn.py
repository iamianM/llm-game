"""Tests for the one-turn pipeline."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.rules import apply_action
from src.game.engine.turn import run_turn
from src.game.state.models import Phase, new_game
from src.game.state.rng import SeededRng


def test_run_turn_applies_action_and_returns_next_actions() -> None:
    """A turn mutates state once and returns the next valid action surface."""
    state = new_game(1)

    result = run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(1),
    )

    assert result.state.turn_index == 1
    assert result.state.islanders[0].relationship.affection == 12
    assert result.available_actions
    assert len(result.state_hash) == 64


def test_run_turn_advances_phase() -> None:
    """ADVANCE_PHASE uses the same run_turn path as other actions."""
    state = new_game(1)

    result = run_turn(state, PlayerAction(kind=ActionKind.ADVANCE_PHASE), SeededRng(1))

    assert result.state.phase is Phase.CHALLENGE
    assert result.state.turn_index == 1


def test_run_turn_surfaces_bombshell_event() -> None:
    """Ceremony events are visible in TurnResult instead of hidden state changes."""
    state = new_game(1)
    state.day = 3
    state.phase = Phase.EVENING

    result = run_turn(state, PlayerAction(kind=ActionKind.ADVANCE_PHASE), SeededRng(1))

    assert any(event.kind == "bombshell" for event in result.ceremony_events)


def test_apply_action_does_not_bump_turn_index() -> None:
    """Turn bookkeeping only happens inside run_turn."""
    state = new_game(1)

    apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(1),
    )

    assert state.turn_index == 0
