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
from src.game.agents.runtime import AgentValidationError
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


def test_curate_player_conversation_survives_curator_raise() -> None:
    """A curator that exhausts its retries and raises must not dead-screen the turn
    on conversation close — curation degrades to the deterministic mock so the
    player and target still record a memory instead of the turn crashing."""
    from src.game.engine.turn_curator import curate_player_conversation

    state = new_game(1)
    _start_conversation(state)
    conversation = state.active_conversation
    assert conversation is not None

    def boom(*_args, **_kwargs) -> MemoryBatch:
        raise AgentValidationError("curator exhausted retries")

    batch = curate_player_conversation(state, conversation, boom)

    assert batch.kind == "player"
    holders = {memory.holder_id for memory in batch.memories}
    assert "player" in holders
    assert conversation.target_id in holders


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
    assert "- holder_id: maya" in rendered
    assert "- holder_id: liam" in rendered
    assert "Valid subject ids:" in rendered


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
    assert fake_client.responses.kwargs["reasoning"] == {"effort": "high", "summary": "detailed"}


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
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )
