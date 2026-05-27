"""Event Narrator agent for ceremonies and bombshell beats.

Design sources:
- 03-LLM-Architecture.md: Event Narrator AI
- 10-Elimination-System.md: Recouplings, Bombshells, Dumpings

Implementation rule:
The Event Narrator describes already-resolved ceremony events. It never picks
who arrives, couples, or leaves.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import cached_property
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict

from src.game.agents.islander_voice import load_dotenv_local
from src.game.agents.runtime import (
    GAME_AGENT_MODEL,
    mark_agent_trace_validation_error,
    reasoning_request_kwargs,
    record_agent_trace,
)
from src.game.engine.ceremonies import CeremonyEvent
from src.game.state.models import GameState

EVENT_NARRATOR_MODEL = GAME_AGENT_MODEL
EVENT_NARRATOR_PROMPT = "src/game/agents/prompts/event_narrator.md"
_EVENT_NARRATOR_PROMPT_FILE = Path(__file__).parent / "prompts" / "event_narrator.md"


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
            instructions=_EVENT_NARRATOR_PROMPT_FILE.read_text(encoding="utf-8"),
            input=_render_context(state, events),
            text_format=EventNarration,
            **reasoning_request_kwargs(),
        )
        narration = response.output_parsed
        record_agent_trace(
            agent_name="event_narrator",
            model=self._model,
            prompt_path=EVENT_NARRATOR_PROMPT,
            response=response,
            output=narration,
        )
        if narration is None:
            raise ValueError("Event Narrator returned no parsed EventNarration")
        try:
            validate_event_narration(narration, events)
        except ValueError as exc:
            mark_agent_trace_validation_error("event_narrator", 1, exc)
            raise
        return narration


def mock_event_narration(state: GameState, events: list[CeremonyEvent]) -> EventNarration:
    """Return deterministic mock event narration for tests and replay."""
    sentences = [_mock_event_sentence(state, event) for event in events]
    if not sentences:
        sentences = ["The villa watches as the moment lands."]
    return EventNarration(prose=" ".join(sentences))


def validate_event_narration(narration: EventNarration, events: list[CeremonyEvent]) -> None:
    """Fail loud if event prose violates the agent boundary.

    Only enforces the structural contract: every named ceremony participant
    must appear in the prose. Prose length, sentence count, and digit
    preferences are conveyed via the prompt, not enforced here.
    """
    prose = narration.prose
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
    semantics = [
        "- recouple_proposal rejected means the target did not accept the player's proposal.",
        "- npc_proposal_incoming means a pending ask, not an accepted recoupling or couple change.",
        "- recoupling narration should name the player's partner when the current couple is known.",
        "- hideaway means the player and named partner leave for a private suite beat.",
    ]
    event_kinds = {event.kind for event in events}
    if "hideaway" in event_kinds and "gather_scheduled" in event_kinds:
        semantics.append(
            "- If hideaway appears with gather_scheduled, narrate only the Hideaway. "
            "The scheduled gather is a later UI/state fact, not part of the private suite beat."
        )
    sections = [
        f"Day: {state.day}",
        f"Phase: {state.phase.value}",
        f"Location: {state.location_id.value}",
        f"Current player couple: {_player_couple(state)}",
        "Event semantics:",
        *semantics,
        "Events:",
        event_lines,
    ]
    # If a round-based minigame just resolved, surface its per-round details so
    # the narrator can name actual picks, reveals, and facets rather than
    # writing generic "ended in success" prose. See docs/minigame-system.md
    # §7 for the narration contract.
    minigame_block = _render_minigame_details(state)
    if minigame_block:
        sections.append(minigame_block)
    sections.append("Narrate these resolved events now. If a Minigame block is "
                    "present above, ground at least one sentence in a concrete "
                    "round detail — a picked answer, a named reveal, a facet, "
                    "or a chemistry pair — using the exact labels shown.")
    return "\n".join(sections)


def _render_minigame_details(state: GameState) -> str:
    """Render the per-round details for a just-resolved round-based minigame.

    Returns an empty string if no round-based minigame is in pending_challenge,
    or if the minigame has not yet been resolved.
    """
    challenge = state.pending_challenge
    if challenge is None or challenge.classification is None or not challenge.rounds:
        return ""
    # Only round-based minigames carry meaningful per-round structure
    # (legacy single-roll resolutions don\'t populate the `rounds` list).
    lines = [
        f"Minigame: {challenge.kind}",
        f"  classification: {challenge.classification}",
        f"  total_points: {challenge.total_points}",
        f"  audience_delta: {challenge.audience_delta}",
        f"  participants: {', '.join(challenge.participants)}",
        "  rounds:",
    ]
    for round_ in challenge.rounds:
        chosen = next((c for c in round_.choices if c.id == round_.chosen_id), None)
        correct = next((c for c in round_.choices if c.is_correct), None)
        chosen_label = repr(chosen.label) if chosen else "(no answer)"
        correct_label = repr(correct.label) if correct else "?"
        outcome = "OK" if (chosen and chosen.is_correct) else "MISS"
        round_meta = []
        if round_.mechanical and round_.trait_key:
            round_meta.append(f"trait={round_.trait_key}")
            round_meta.append(f"tier={round_.tier}")
        elif round_.trait_key:
            round_meta.append(f"flavor_key={round_.trait_key}")
        if round_.target_id:
            round_meta.append(f"target={round_.target_id}")
        meta_str = (" (" + ", ".join(round_meta) + ")") if round_meta else ""
        lines.append(
            f"    r{round_.index + 1} [{outcome}] {round_.stem!r}{meta_str}"
        )
        lines.append(f"        chose {chosen_label}; correct was {correct_label}; points {round_.points}")
        for reveal in round_.reveals:
            payload_summary = ", ".join(f"{k}={v}" for k, v in reveal.payload.items())
            lines.append(f"        reveal[{reveal.kind}] subject={reveal.subject_id} {payload_summary}")
    return "\n".join(lines)


def _player_couple(state: GameState) -> str:
    for couple in state.couples:
        members = {couple.partner_a_id, couple.partner_b_id}
        if "player" not in members:
            continue
        partner_id = next((member for member in members if member != "player"), None)
        if partner_id is None:
            return "player is single"
        return f"player with {partner_id} ({_name_for(state, partner_id)})"
    return "player is single"
