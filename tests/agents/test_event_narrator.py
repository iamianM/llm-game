"""Opt-in tests for real Event Narrator output."""

from __future__ import annotations

import pytest

from src.game.agents.event_narrator import OpenAIEventNarrator, validate_event_narration
from src.game.engine.ceremonies import CeremonyEvent
from src.game.state.models import new_game


@pytest.mark.llm
@pytest.mark.parametrize(
    "events",
    [
        [CeremonyEvent(kind="bombshell", message="Aisha enters the villa.", islander_id="aisha")],
        [CeremonyEvent(kind="recoupling", message="Chloe couples with the player.", islander_id="chloe")],
        [CeremonyEvent(kind="elimination", message="Liam leaves the villa.", islander_id="liam")],
    ],
)
def test_event_narrator_output_contract(events: list[CeremonyEvent]) -> None:
    """Event Narrator prose stays bounded and references supplied participants."""
    state = new_game(1)
    agent = OpenAIEventNarrator()

    narration = agent.narrate(state, events)

    validate_event_narration(narration, events)
