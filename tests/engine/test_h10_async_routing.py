"""Tests for H10.3 model routing and async resort application."""

from __future__ import annotations

import asyncio

from src.game.agents.background_dialogue import (
    BACKGROUND_DIALOGUE_MODEL,
    mock_background_dialogue,
)
from src.game.agents.contextual_options import CONTEXTUAL_OPTIONS_MODEL
from src.game.agents.conversation_curator import CONVERSATION_CURATOR_MODEL
from src.game.agents.resort_orchestrator import NewConversation, ResortUpdate
from src.game.agents.runtime import GAME_AGENT_MODEL, GAME_AGENT_REASONING_EFFORT
from src.game.agents.turn_agents import mock_turn_agents
from src.game.engine.resort import apply_resort_update_async
from src.game.state.models import GameState, Location, NPCNPCConversation, new_game
from src.game.state.rng import SeededRng


def test_h10_model_routing_constants() -> None:
    assert GAME_AGENT_MODEL == "gpt-5.4-mini"
    assert GAME_AGENT_REASONING_EFFORT == "high"
    assert CONVERSATION_CURATOR_MODEL == GAME_AGENT_MODEL
    assert BACKGROUND_DIALOGUE_MODEL == GAME_AGENT_MODEL
    assert CONTEXTUAL_OPTIONS_MODEL == GAME_AGENT_MODEL


def test_apply_resort_update_async_accepts_parallel_background_callables() -> None:
    state = new_game(1)
    for heartbreaker in state.heartbreakers[:4]:
        heartbreaker.location_id = Location.POOL
    first_pair = [state.heartbreakers[0].id, state.heartbreakers[1].id]
    second_pair = [state.heartbreakers[2].id, state.heartbreakers[3].id]
    update = ResortUpdate(
        conversation_starts=[
            NewConversation(participants=first_pair, location=Location.POOL, topic="pool gossip"),
            NewConversation(
                participants=second_pair, location=Location.POOL, topic="resort strategy"
            ),
        ]
    )

    async def background(
        game_state: GameState,
        conversation: NPCNPCConversation,
        nudge: str = "",
    ):
        await asyncio.sleep(0)
        return mock_background_dialogue(game_state, conversation, nudge)

    changes = asyncio.run(
        apply_resort_update_async(
            state,
            update,
            SeededRng(1),
            background_dialogue=background,
            conversation_curator=mock_turn_agents().conversation_curator,
        )
    )

    assert len(changes.background_dialogues) == 2
    assert len(state.npc_conversations) == 2
    assert all(len(conversation.exchanges) == 1 for conversation in state.npc_conversations)
