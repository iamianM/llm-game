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


def test_villa_orchestrator_context_marks_isolated_player() -> None:
    state = new_game(1)
    for islander in state.islanders:
        islander.location_id = Location.KITCHEN

    rendered = _render_context(state)

    assert "Player isolation: player is alone at pool" in rendered


@pytest.mark.llm
def test_villa_orchestrator_contract() -> None:
    """Real Orchestrator returns an update the engine can validate."""
    state = new_game(1)
    agent = OpenAIVillaOrchestrator()

    update = agent.decide(state)

    validate_villa_update(state, update)


@pytest.mark.llm
def test_orchestrator_draws_npc_toward_isolated_player() -> None:
    """With an isolated player, the Orchestrator should tend toward movement."""
    state = new_game(7)
    for islander in state.islanders:
        islander.location_id = Location.KITCHEN

    update = OpenAIVillaOrchestrator().decide(state)

    assert any(movement.target_location is Location.POOL for movement in update.npc_movements)


@pytest.mark.llm
def test_orchestrator_produces_at_least_one_movement_per_two_turns_avg() -> None:
    """Claude's H9.7 prompt should make movement common, not static."""
    movements = 0
    for seed in range(20, 26):
        state = new_game(seed)
        update = OpenAIVillaOrchestrator().decide(state)
        movements += len(update.npc_movements)

    assert movements >= 3
