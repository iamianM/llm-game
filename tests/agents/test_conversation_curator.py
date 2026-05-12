"""Tests for Conversation Curator memory commits."""

from __future__ import annotations

import pytest

from src.game.agents.contextual_options import mock_follow_up_menu
from src.game.agents.conversation_curator import (
    OpenAIConversationCurator,
    mock_conversation_curator,
    validate_memory_batch,
)
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.turn import run_turn
from src.game.state.models import new_game
from src.game.state.rng import SeededRng


def test_mock_curator_returns_participant_memories() -> None:
    """Mock curator uses the same typed batch shape as the live agent."""
    state = new_game(1)
    _start_conversation(state)
    conversation = state.active_conversation
    assert conversation is not None

    batch = mock_conversation_curator(state, conversation)

    validate_memory_batch(batch, state, {"player", "chloe"}, set())
    assert {memory.holder_id for memory in batch.memories} == {"player", "chloe"}


@pytest.mark.llm
def test_conversation_curator_output_contract() -> None:
    """Real Curator returns parseable, valid memory commits."""
    state = new_game(1)
    _start_conversation(state)
    conversation = state.active_conversation
    assert conversation is not None
    agent = OpenAIConversationCurator()

    batch = agent.curate(state, conversation)

    validate_memory_batch(batch, state, {"player", "chloe"}, set())


def _start_conversation(state) -> None:
    run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(1),
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )
