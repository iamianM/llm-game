"""Opt-in tests for real Event Narrator output."""

from __future__ import annotations

import pytest

from src.game.agents.event_narrator import (
    EventNarration,
    OpenAIEventNarrator,
    mock_event_narration,
    validate_event_narration,
)
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


def test_event_narrator_validation_accepts_starting_cast_display_name() -> None:
    """Starting-cast ids may appear in prose as their public first name."""
    validate_event_narration(
        narration=EventNarration(
            prose="The firepit falls quiet as Jordan faces the decision. Every glance sharpens, and the villa absorbs the shock."
        ),
        events=[
            CeremonyEvent(
                kind="elimination",
                message="Jordan leaves the villa.",
                islander_id="jordan_start",
            )
        ],
    )


def test_mock_event_narration_uses_player_facing_event_language() -> None:
    state = new_game(1)

    narration = mock_event_narration(
        state,
        [
            CeremonyEvent(kind="recoupling", message="internal recouple completed"),
            CeremonyEvent(kind="elimination", message="jordan_start leaves", islander_id="jordan_start"),
        ],
    )

    assert "Pairing Ceremony" in narration.prose
    assert "Jordan is Heart Out" in narration.prose
    assert "jordan_start" not in narration.prose
