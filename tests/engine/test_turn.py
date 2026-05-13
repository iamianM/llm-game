"""Tests for the one-turn pipeline."""

from __future__ import annotations

from src.game.agents.contextual_options import mock_follow_up_menu
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.rules import apply_action
from src.game.engine.turn import run_turn
from src.game.state.models import MemoryBatch, MemoryDraft, Phase, new_game
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
    assert result.exchange is not None
    assert result.exchange.npc_dialogue
    assert result.available_actions
    assert len(result.state_hash) == 64


def test_run_turn_advances_phase() -> None:
    """ADVANCE_PHASE uses the same run_turn path as other actions."""
    state = new_game(1)

    result = run_turn(state, PlayerAction(kind=ActionKind.ADVANCE_PHASE), SeededRng(1))

    assert result.state.phase is Phase.CHALLENGE
    assert result.state.turn_index == 1


def test_run_turn_surfaces_casa_amor_arrival_event() -> None:
    """Ceremony events are visible in TurnResult instead of hidden state changes."""
    state = new_game(1)
    state.day = 4
    state.phase = Phase.TEXT

    result = run_turn(state, PlayerAction(kind=ActionKind.ADVANCE_PHASE), SeededRng(1))

    assert any(event.kind == "casa_amor_arrival" for event in result.ceremony_events)
    assert result.event_narration is not None


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


def test_wheel_exit_closes_conversation_and_applies_trust_bonus() -> None:
    """A wheel exit produces a goodbye exchange, curates, and closes."""
    state = new_game(1)
    rng = SeededRng(1)
    run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        rng,
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )
    calls = 0

    def curator(*_args) -> MemoryBatch:
        nonlocal calls
        calls += 1
        return MemoryBatch(
            memories=[
                MemoryDraft(
                    holder_id="player",
                    subject_id="chloe",
                    content="I ended the chat warmly.",
                    source="direct",
                    emotional_weight=3,
                    tags=["exit"],
                )
            ]
        )

    result = run_turn(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, intent_id="end_softly"),
        rng,
        contextual_options=lambda *_args: mock_follow_up_menu(),
        conversation_curator=curator,
    )

    assert result.exchange is not None
    assert result.state.active_conversation is None
    assert result.mechanical_result.relationship_deltas["chloe"].trust == 1
    assert calls == 1
    assert result.curator_batches


def test_walk_away_closes_conversation_and_applies_affection_penalty() -> None:
    """Top-level END_CONVERSATION is a curt walk-away, not a graceful wheel exit."""
    state = new_game(1)
    rng = SeededRng(1)
    run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        rng,
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )
    affection_before = state.islanders[0].relationship.affection
    calls = 0

    def curator(*_args) -> MemoryBatch:
        nonlocal calls
        calls += 1
        return MemoryBatch(
            memories=[
                MemoryDraft(
                    holder_id="player",
                    subject_id="chloe",
                    content="I walked away from the chat.",
                    source="direct",
                    emotional_weight=4,
                    tags=["walked_away"],
                )
            ]
        )

    result = run_turn(
        state,
        PlayerAction(kind=ActionKind.END_CONVERSATION),
        rng,
        conversation_curator=curator,
    )

    assert result.exchange is None
    assert result.state.active_conversation is None
    assert state.islanders[0].relationship.affection == affection_before - 1
    assert result.mechanical_result.relationship_deltas["chloe"].affection == -1
    assert calls == 1
    assert result.curator_batches
