"""Tests for deterministic conversation lifecycle helpers."""

from __future__ import annotations

import pytest

from src.game.agents.contextual_options import mock_follow_up_menu
from src.game.agents.heartbreaker_voice import Exchange
from src.game.engine.actions import ActionKind, PlayerAction, available_actions, validate_action
from src.game.engine.conversation import (
    append_exchange,
    close_conversation,
    departure_probability,
    start_conversation,
)
from src.game.engine.rules import MechanicalResult
from src.game.state.models import Mood, RelationshipDelta, new_game


def test_conversation_lifecycle_start_append_close() -> None:
    """Conversation helpers open, retain an exchange, then close cleanly."""
    state = new_game(1)

    conversation = start_conversation(state, "chloe", 0)
    append_exchange(conversation, _result(success=True), _exchange(), turn_index=1)
    close_conversation(state, "player_exit")

    assert state.active_conversation is None
    assert conversation.exchanges[0].intent_id == "friendly_chat_resort"


def test_departure_probability_rises_after_miss() -> None:
    """Awkward recent exchanges increase departure probability."""
    state = new_game(1)
    conversation = start_conversation(state, "chloe", 0)
    append_exchange(conversation, _result(success=False), _exchange(), turn_index=1)

    assert departure_probability(conversation, state) >= 25


def test_departure_probability_drops_for_vulnerable_success() -> None:
    """Vulnerable successful conversations make NPCs more likely to stay."""
    state = new_game(1)
    conversation = start_conversation(state, "chloe", 0)
    append_exchange(
        conversation,
        _result(success=True, tags=["deep", "vulnerable"]),
        _exchange(),
        turn_index=1,
    )

    assert departure_probability(conversation, state) == 0


def test_cannot_start_two_conversations() -> None:
    """Validation blocks nested one-on-one conversations."""
    state = new_game(1)
    start_conversation(state, "chloe", 0)

    with pytest.raises(ValueError, match="active"):
        validate_action(
            state,
            PlayerAction(
                kind=ActionKind.START_CONVERSATION,
                target_id="chloe",
                intent_id="friendly_chat_resort",
            ),
        )


def test_open_conversation_surfaces_followups_only() -> None:
    """Open conversations expose follow-ups plus END_CONVERSATION."""
    state = new_game(1)
    conversation = start_conversation(state, "chloe", 0)
    conversation.pending_options = mock_follow_up_menu("joke_back")

    actions = [spec.action.kind for spec in available_actions(state)]

    assert actions == [ActionKind.RESPOND_WITH, ActionKind.RESPOND_WITH, ActionKind.END_CONVERSATION]


def test_cannot_respond_when_closed() -> None:
    """A follow-up response requires an active conversation."""
    state = new_game(1)

    with pytest.raises(ValueError, match="active conversation"):
        validate_action(state, PlayerAction(kind=ActionKind.RESPOND_WITH, option_index=0))


def _exchange() -> Exchange:
    return Exchange(
        player_dialogue="I wanted to check in properly and see where your head is at.",
        npc_dialogue="*nods* I appreciate that. It feels good to have a real conversation.",
        npc_tone="warm",
        npc_mood_after=Mood.CONTENT,
    )


def _result(*, success: bool, tags: list[str] | None = None) -> MechanicalResult:
    return MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        success=success,
        relationship_deltas={"chloe": RelationshipDelta(affection=2 if success else -1)},
        tags=["friendly"] if tags is None else tags,
    )
