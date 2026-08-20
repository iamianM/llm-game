"""Opt-in tests for real Resort Orchestrator output."""

from __future__ import annotations

import pytest

from src.game.agents.resort_orchestrator import (
    OpenAIResortOrchestrator,
    _render_context,
    mock_resort_orchestrator,
)
from src.game.engine.resort import validate_resort_update
from src.game.state.models import Location, NPCNPCConversation, new_game


def test_mock_resort_orchestrator_contract() -> None:
    """Mock orchestrator returns a valid empty update."""
    state = new_game(1)

    update = mock_resort_orchestrator(state)

    validate_resort_update(state, update)


def test_resort_orchestrator_context_marks_conversation_participants_locked() -> None:
    state = new_game(1)
    state.heartbreakers[1].location_id = Location.POOL
    state.heartbreakers[2].location_id = Location.POOL
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


def test_resort_orchestrator_context_marks_isolated_player() -> None:
    state = new_game(1)
    for heartbreaker in state.heartbreakers:
        heartbreaker.location_id = Location.KITCHEN

    rendered = _render_context(state)

    assert "Player isolation: player is alone at pool" in rendered


def test_resort_orchestrator_context_makes_movement_and_starts_atomic() -> None:
    state = new_game(1)

    rendered = _render_context(state)

    assert "Atomic movement-and-conversation contract" in rendered
    assert "both participants' final locations" in rendered
    assert "target_location must be identical" in rendered


@pytest.mark.llm
def test_resort_orchestrator_contract() -> None:
    """Real Orchestrator returns an update the engine can validate."""
    state = new_game(1)
    agent = OpenAIResortOrchestrator()

    update = agent.decide(state)

    validate_resort_update(state, update)


@pytest.mark.llm
def test_orchestrator_draws_npc_toward_isolated_player() -> None:
    """With an isolated player, the Orchestrator should tend toward movement."""
    state = new_game(7)
    for heartbreaker in state.heartbreakers:
        heartbreaker.location_id = Location.KITCHEN

    update = OpenAIResortOrchestrator().decide(state)

    assert any(movement.target_location is Location.POOL for movement in update.npc_movements)


@pytest.mark.llm
def test_orchestrator_produces_at_least_one_movement_per_two_turns_avg() -> None:
    """Claude's H9.7 prompt should make movement common, not static."""
    movements = 0
    for seed in range(20, 26):
        state = new_game(seed)
        update = OpenAIResortOrchestrator().decide(state)
        movements += len(update.npc_movements)

    assert movements >= 3
