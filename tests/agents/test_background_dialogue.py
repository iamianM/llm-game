"""Opt-in tests for real Background Dialogue output."""

from __future__ import annotations

import pytest

from src.game.agents.background_dialogue import (
    OpenAIBackgroundDialogue,
    mock_background_dialogue,
    validate_background_exchange,
)
from src.game.state.models import Location, NPCNPCConversation, new_game


def test_mock_background_dialogue_contract() -> None:
    """Mock background dialogue satisfies the same validator as live output."""
    state = new_game(1)
    conversation = _conversation()

    exchange = mock_background_dialogue(state, conversation)

    validate_background_exchange(exchange)


@pytest.mark.llm
def test_background_dialogue_contract() -> None:
    """Real Background Dialogue returns a valid NPC-NPC exchange."""
    state = new_game(1)
    conversation = _conversation()
    agent = OpenAIBackgroundDialogue()

    exchange = agent.generate(state, conversation, "getting more gossipy")

    validate_background_exchange(exchange)


def _conversation() -> NPCNPCConversation:
    return NPCNPCConversation(
        id="npcconv_test",
        participants=["chloe", "maya"],
        location_id=Location.POOL,
        topic="comparing notes about the new bombshell",
        started_on_turn=1,
    )
