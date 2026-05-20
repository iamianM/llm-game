"""Event Narrator agent for ceremonies and bombshell beats.

Design sources:
- 03-LLM-Architecture.md: Event Narrator AI
- 10-Elimination-System.md: Recouplings, Bombshells, Dumpings

Implementation rule:
The Event Narrator describes already-resolved ceremony events. It never picks
who arrives, couples, or leaves.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from functools import cached_property
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict

from src.game.agents.islander_voice import load_dotenv_local
from src.game.engine.ceremonies import CeremonyEvent
from src.game.state.models import GameState

EVENT_NARRATOR_MODEL = "gpt-4.1-mini"


class EventNarration(BaseModel):
    """Narration for one set of resolved ceremony events."""

    model_config = ConfigDict(extra="forbid")

    prose: str


EventNarratorFn = Callable[[GameState, list[CeremonyEvent]], EventNarration]


class OpenAIEventNarrator:
    """Single event narrator backed by the OpenAI Responses API."""

    def __init__(self, *, model: str = EVENT_NARRATOR_MODEL) -> None:
        load_dotenv_local()
        self._model = model

    @cached_property
    def _client(self) -> OpenAI:
        return OpenAI()

    def narrate(self, state: GameState, events: list[CeremonyEvent]) -> EventNarration:
        """Generate narration for resolved ceremony events."""
        if not events:
            raise ValueError("event narration requires at least one ceremony event")
        response = self._client.responses.parse(
            model=self._model,
            instructions=Path("src/game/agents/prompts/event_narrator.md").read_text(
                encoding="utf-8"
            ),
            input=_render_context(state, events),
            text_format=EventNarration,
            max_output_tokens=220,
        )
        narration = response.output_parsed
        if narration is None:
            raise ValueError("Event Narrator returned no parsed EventNarration")
        validate_event_narration(narration, events)
        return narration


def mock_event_narration(state: GameState, events: list[CeremonyEvent]) -> EventNarration:
    """Return deterministic mock event narration for tests and replay."""
    messages = [_mock_event_sentence(state, event) for event in events]
    return EventNarration(prose=" ".join(messages))


def validate_event_narration(narration: EventNarration, events: list[CeremonyEvent]) -> None:
    """Fail loud if event prose violates the contract."""
    prose = narration.prose
    sentences = [part for part in re.split(r"[.!?]+", prose) if part.strip()]
    if not 2 <= len(sentences) <= 4:
        raise ValueError(f"event narration sentence count out of bounds: {prose!r}")
    if re.search(r"\d", prose):
        raise ValueError(f"event narration contains digits: {prose!r}")
    required = [event.islander_id for event in events if event.islander_id is not None]
    lower_prose = prose.lower()
    missing = [name for name in required if not _mentions_participant(lower_prose, name)]
    if missing:
        raise ValueError(f"event narration omitted participant(s) {missing}: {prose!r}")


def _mentions_participant(lower_prose: str, islander_id: str) -> bool:
    aliases = {islander_id.lower(), islander_id.lower().replace("_", " ")}
    if islander_id.endswith("_start"):
        aliases.add(islander_id.removesuffix("_start").lower())
    return any(alias in lower_prose for alias in aliases)


def _mock_event_sentence(state: GameState, event: CeremonyEvent) -> str:
    if event.kind == "recoupling":
        return "At the firepit, the Pairing Ceremony locks in the next couples."
    if event.kind == "elimination":
        return f"{_name_for(state, event.islander_id)} is Heart Out, and Sunset Bay feels the shift."
    if event.kind == "challenge":
        return f"The {_event_label(event.sub_kind or event.kind)} result lands, changing the mood around the pool."
    if event.kind == "casa_amor_arrival":
        return "Flush of Hearts opens, sending you into the second villa with every connection under pressure."
    if event.kind == "casa_amor_return_reveal":
        return f"The Sunset Bay return reveal: {event.message}"
    return event.message


def _name_for(state: GameState, actor_id: str | None) -> str:
    if actor_id is None:
        return "Someone"
    if actor_id == "player":
        return "You"
    for islander in state.islanders:
        if islander.id == actor_id:
            return islander.name
    return actor_id


def _event_label(kind: str) -> str:
    labels = {
        "challenge": "Challenge",
        "compatibility_quiz": "Compatibility Quiz",
        "final_couples": "Final Couples Challenge",
        "heart_rate": "Pulse Race",
        "lie_detector": "Lie Detector",
        "mr_and_mrs": "The Couples Quiz",
        "snog_marry_pie": "Kiss Wed Pass",
    }
    return labels.get(kind, kind.replace("_", " ").title())


def _render_context(state: GameState, events: list[CeremonyEvent]) -> str:
    event_lines = "\n".join(
        f"- {event.kind}: {event.message} ({event.islander_id or 'no named islander'})"
        for event in events
    )
    return "\n".join(
        [
            f"Day: {state.day}",
            f"Phase: {state.phase.value}",
            f"Location: {state.location_id.value}",
            "Events:",
            event_lines,
            "Narrate these resolved events now.",
        ]
    )
