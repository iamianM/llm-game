"""Opt-in tests for real Villa Orchestrator output."""

from __future__ import annotations

import pytest

from src.game.agents.villa_orchestrator import OpenAIVillaOrchestrator, mock_villa_orchestrator
from src.game.engine.villa import validate_villa_update
from src.game.state.models import new_game


def test_mock_villa_orchestrator_contract() -> None:
    """Mock orchestrator returns a valid empty update."""
    state = new_game(1)

    update = mock_villa_orchestrator(state)

    validate_villa_update(state, update)


@pytest.mark.llm
def test_villa_orchestrator_contract() -> None:
    """Real Orchestrator returns an update the engine can validate."""
    state = new_game(1)
    agent = OpenAIVillaOrchestrator()

    update = agent.decide(state)

    validate_villa_update(state, update)
