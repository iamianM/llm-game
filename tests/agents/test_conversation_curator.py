"""Tests for Conversation Curator memory commits."""

from __future__ import annotations

from dataclasses import replace

import pytest

from src.game.agents.contextual_options import mock_follow_up_menu
from src.game.agents.conversation_curator import (
    OpenAIConversationCurator,
    _has_specific_future_commitment,
    _render_context,
    mock_conversation_curator,
    validate_memory_batch,
)
from src.game.agents.runtime import AgentValidationError
from src.game.agents.turn_agents import mock_turn_agents
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


def test_curate_player_conversation_propagates_curator_raise() -> None:
    """A configured curator failure is visible to the atomic turn boundary."""
    from src.game.engine.turn_curator import curate_player_conversation

    state = new_game(1)
    _start_conversation(state)
    conversation = state.active_conversation
    assert conversation is not None

    def boom(*_args, **_kwargs) -> MemoryBatch:
        raise AgentValidationError("curator exhausted retries")

    with pytest.raises(AgentValidationError, match="curator exhausted retries"):
        curate_player_conversation(state, conversation, boom)


def test_curator_context_lists_eligible_memory_holders() -> None:
    state = new_game(1)
    conversation = NPCNPCConversation(
        id="npcconv_context",
        participants=["maya", "liam"],
        location_id=Location.POOL,
        topic="testing memory requirements",
        started_on_turn=0,
    )

    rendered = _render_context(state, conversation, [])

    assert "Eligible direct memory holders: maya, liam" in rendered
    assert "- holder_id: maya" in rendered
    assert "- holder_id: liam" in rendered
    assert "Valid subject ids:" in rendered


def test_curator_accepts_empty_batch_for_routine_conversation() -> None:
    state = new_game(1)
    _start_conversation(state)

    validate_memory_batch(
        MemoryBatch(memories=[], summary="The chat ended without a lasting reveal."),
        state,
        {"player", "chloe"},
        set(),
    )


def test_curator_requires_both_holders_for_a_meaningful_boundary() -> None:
    state = new_game(1)

    with pytest.raises(ValueError, match="missing memory holders.*chloe"):
        validate_memory_batch(
            MemoryBatch(
                memories=[
                    MemoryDraft(
                        holder_id="player",
                        subject_id="chloe",
                        content="Chloe said she was not ready to discuss family, so I did not push.",
                        source="direct",
                        emotional_weight=3,
                        tags=["boundary", "respect"],
                    )
                ]
            ),
            state,
            {"player", "chloe"},
            set(),
            required_memory_holders={"player", "chloe"},
        )


def test_curator_limits_routine_player_conversation_to_one_memory() -> None:
    state = new_game(1)

    with pytest.raises(ValueError, match="maximum is 1"):
        validate_memory_batch(
            MemoryBatch(
                memories=[
                    MemoryDraft(
                        holder_id="player",
                        subject_id="chloe",
                        content="Chloe said she spends her evenings marking books.",
                        source="direct",
                        emotional_weight=3,
                        tags=["school", "routine"],
                    ),
                    MemoryDraft(
                        holder_id="chloe",
                        subject_id="player",
                        content="The player said home has felt unsettled lately.",
                        source="direct",
                        emotional_weight=4,
                        tags=["home", "vulnerable"],
                    ),
                ]
            ),
            state,
            {"player", "chloe"},
            set(),
            max_memories=1,
        )


def test_curator_requires_memory_for_specific_future_commitment() -> None:
    state = new_game(1)
    _start_conversation(state)
    conversation = state.active_conversation
    assert conversation is not None
    conversation.exchanges[-1].npc_dialogue = (
        "Thanks, love. I enjoyed it too, and I'll save you a lounger next time."
    )

    assert _has_specific_future_commitment(conversation) is True
    with pytest.raises(ValueError, match="minimum is 1"):
        validate_memory_batch(
            MemoryBatch(memories=[], summary="They agreed to chat again."),
            state,
            {"player", "chloe"},
            set(),
            min_memories=1,
            max_memories=1,
        )


def test_curator_detects_curly_apostrophe_future_meeting() -> None:
    state = new_game(1)
    _start_conversation(state)
    conversation = state.active_conversation
    assert conversation is not None
    conversation.exchanges[-1].npc_dialogue = "I’ll see you by the pool later."

    assert _has_specific_future_commitment(conversation) is True


def test_curator_detects_specific_future_continuation() -> None:
    state = new_game(1)
    _start_conversation(state)
    conversation = state.active_conversation
    assert conversation is not None
    conversation.exchanges[-1].npc_dialogue = (
        "I will let you get back to the pool, but we can pick this up over breakfast."
    )

    assert _has_specific_future_commitment(conversation) is True


def test_curator_rejects_trivial_single_exchange_memory() -> None:
    state = new_game(1)

    with pytest.raises(ValueError, match="trivial low-weight memory"):
        validate_memory_batch(
            MemoryBatch(
                memories=[
                    MemoryDraft(
                        holder_id="player",
                        subject_id="jordan",
                        content="Jordan said he felt restless but alright by the pool.",
                        source="direct",
                        emotional_weight=1,
                        tags=["check_in", "mood"],
                        durable=False,
                    )
                ]
            ),
            state,
            {"player", "jordan"},
            set(),
            max_memories=1,
            reject_trivial_memories=True,
        )


def test_curator_context_supplies_pronouns_so_unisex_names_are_not_guessed() -> None:
    """Every participant's pronouns must reach the curator. A unisex name like
    Jules (male in our cast) was getting "she" in recap memories because the
    context only gave the name — the model guessed gender. The render must spell
    out he/him or she/her for each holder so the LLM never has to infer it."""
    state = new_game(1)
    _start_conversation(state)
    conversation = state.active_conversation
    assert conversation is not None
    chloe = next(heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == "chloe")

    rendered = _render_context(state, conversation, [])

    assert "Pronouns (use exactly these" in rendered
    expected = "she/her" if chloe.gender.value == "woman" else "he/him"
    assert f"- chloe: {chloe.name} ({expected})" in rendered
    player_pronouns = "she/her" if state.player.gender.value == "woman" else "he/him"
    assert f"- player: {state.player.name} ({player_pronouns})" in rendered


def test_curator_request_uses_shared_reasoning_kwargs_without_token_cap() -> None:
    """The curator request must not pass max_output_tokens or temperature."""

    class FakeResponses:
        def __init__(self) -> None:
            self.kwargs: dict[str, object] = {}

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

    assert "max_output_tokens" not in fake_client.responses.kwargs
    assert "temperature" not in fake_client.responses.kwargs
    assert fake_client.responses.kwargs["reasoning"] == {"effort": "medium", "summary": "detailed"}


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
            intent_id="friendly_chat_resort",
        ),
        SeededRng(1),
        replace(
            mock_turn_agents(),
            contextual_options=lambda *_args: mock_follow_up_menu(),
        ),
    )
