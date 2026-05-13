"""Tests for Conversation Curator memory commits."""

from __future__ import annotations

import pytest

from src.game.agents.contextual_options import mock_follow_up_menu
from src.game.agents.conversation_curator import (
    OpenAIConversationCurator,
    _render_context,
    mock_conversation_curator,
    validate_memory_batch,
)
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.turn import run_turn
from src.game.state.models import Location, MemoryBatch, MemoryDraft, NPCNPCConversation, new_game
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


def test_curator_context_lists_required_memory_holders() -> None:
    state = new_game(1)
    conversation = NPCNPCConversation(
        id="npcconv_context",
        participants=["maya", "liam"],
        location_id=Location.POOL,
        topic="testing memory requirements",
        started_on_turn=0,
    )

    rendered = _render_context(state, conversation, [])

    assert "Required direct memory holders: maya, liam" in rendered


def test_curator_parse_budget_fits_three_output_schema() -> None:
    """The expanded MemoryBatch shape needs enough tokens to avoid truncation."""

    class FakeResponses:
        def __init__(self) -> None:
            self.kwargs = {}

        def parse(self, **kwargs):
            self.kwargs = kwargs

            class ParsedResponse:
                output_parsed = MemoryBatch(
                    memories=[
                        MemoryDraft(
                            holder_id="player",
                            subject_id="chloe",
                            content="I remember Chloe being honest by the pool.",
                            source="direct",
                            emotional_weight=5,
                            tags=["honest"],
                        )
                    ],
                    summary="Player and Chloe had an honest pool conversation.",
                    gossip_seeds=[],
                )

            return ParsedResponse()

    class FakeClient:
        def __init__(self) -> None:
            self.responses = FakeResponses()

    agent = OpenAIConversationCurator()
    fake_client = FakeClient()
    agent.__dict__["_client"] = fake_client

    agent._generate_batch("context")

    assert fake_client.responses.kwargs["max_output_tokens"] >= 1800


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
