"""Opt-in tests for real Villa Orchestrator output."""

from __future__ import annotations

import pytest

from src.game.agents.villa_orchestrator import (
    OpenAIVillaOrchestrator,
    _render_context,
    mock_villa_orchestrator,
)
from src.game.engine.villa import validate_villa_update
from src.game.state.models import Location, NPCNPCConversation, new_game


def test_mock_villa_orchestrator_contract() -> None:
    """Mock orchestrator returns a valid empty update."""
    state = new_game(1)

    update = mock_villa_orchestrator(state)

    validate_villa_update(state, update)


def test_villa_orchestrator_context_marks_conversation_participants_locked() -> None:
    state = new_game(1)
    state.islanders[1].location_id = Location.POOL
    state.islanders[2].location_id = Location.POOL
    state.npc_conversations.append(
        NPCNPCConversation(
            id="npcconv_locked",
            participants=["maya", "liam"],
            location_id=Location.POOL,
            topic="testing movement constraints",
            started_on_turn=0,
        )
    )

    rendered = _render_context(state)

    assert "npcconv_locked: maya, liam are locked in conversation" in rendered
    assert "do not use npc_movements" in rendered


@pytest.mark.llm
def test_villa_orchestrator_contract() -> None:
    """Real Orchestrator returns an update the engine can validate."""
    state = new_game(1)
    agent = OpenAIVillaOrchestrator()

    update = agent.decide(state)

    validate_villa_update(state, update)
