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
from pydantic import BaseModel, ConfigDict, ValidationError

from src.game.agents.islander_voice import load_dotenv_local
from src.game.agents.runtime import (
    GAME_AGENT_MODEL,
    AgentGenerationError,
    AgentValidationError,
    begin_agent_attempt,
    build_game_client,
    end_agent_attempt,
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
        return build_game_client()

    def narrate(self, state: GameState, events: list[CeremonyEvent]) -> EventNarration:
        """Generate narration for resolved ceremony events.

        Retries on validation failure, feeding the error back so the model can
        correct a leaked engine token rather than crashing the turn.
        """
        if not events:
            raise ValueError("event narration requires at least one ceremony event")
        rendered = _render_context(state, events)
        last_error: ValueError | None = None
        for attempt in range(3):
            attempt_number = attempt + 1
            retry_context = rendered
            if last_error is not None:
                retry_context = (
                    f"{rendered}\n\n"
                    "The previous narration failed validation. "
                    f"Validation error: {last_error}. "
                    "Rewrite the prose in natural language: refer to people only "
                    "by name (the player is \"you\") and never include ids, "
                    "snake_case keys, underscores, or key=value metadata."
                )
            attempt_token = begin_agent_attempt(attempt_number)
            try:
                try:
                    narration = self._generate_narration(retry_context)
                except Exception as exc:
                    mark_agent_trace_validation_error("event_narrator", attempt_number, exc)
                    last_error = ValueError(str(exc))
                    if attempt == 2:
                        raise AgentGenerationError(str(exc)) from exc
                    continue
            finally:
                end_agent_attempt(attempt_token)
            try:
                validate_event_narration(narration, events)
                return narration
            except (ValueError, ValidationError) as exc:
                mark_agent_trace_validation_error("event_narrator", attempt_number, exc)
                last_error = ValueError(str(exc))
                if attempt == 2:
                    raise AgentValidationError(str(exc)) from exc
        raise AssertionError("unreachable event narrator retry state")

    def _generate_narration(self, rendered_context: str) -> EventNarration:
        """Request one parsed EventNarration from the model."""
        response = self._client.responses.parse(
            model=self._model,
            instructions=_EVENT_NARRATOR_PROMPT_FILE.read_text(encoding="utf-8"),
            input=rendered_context,
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
        return narration


def mock_event_narration(state: GameState, events: list[CeremonyEvent]) -> EventNarration:
    """Return deterministic mock event narration for tests and replay."""
    sentences = [_mock_event_sentence(state, event) for event in events]
    if not sentences:
        sentences = ["The villa watches as the moment lands."]
    return EventNarration(prose=" ".join(sentences))


def validate_event_narration(narration: EventNarration, events: list[CeremonyEvent]) -> None:
    """Fail loud if event prose violates the agent boundary.

    Enforces two contracts:
    1. Every named ceremony participant must appear in the prose.
    2. No engine-internal token leaks into player-facing prose: raw
       snake_case keys/ids (e.g. "drink_of_choice", "sam_ht") and
       bracketed `key=value` metadata are forbidden. Prose length, sentence
       count, and digit preferences are conveyed via the prompt, not enforced
       here.
    """
    prose = narration.prose
    leaked = _leaked_tokens(prose)
    if leaked:
        raise ValueError(
            f"event narration leaked engine token(s) {leaked}: {prose!r}"
        )
    required = [event.islander_id for event in events if event.islander_id is not None]
    lower_prose = prose.lower()
    missing = [name for name in required if not _mentions_participant(lower_prose, name)]
    if missing:
        raise ValueError(f"event narration omitted participant(s) {missing}: {prose!r}")


# A snake_case token: two or more lowercase/digit runs joined by underscores
# (e.g. "drink_of_choice", "sam_ht"). Natural prose never contains these.
_SNAKE_TOKEN = re.compile(r"\b[a-z0-9]+(?:_[a-z0-9]+)+\b")
# Bracketed key=value metadata that should have been translated to prose.
_KV_TOKEN = re.compile(r"\b[a-zA-Z]\w*=")


def _leaked_tokens(prose: str) -> list[str]:
    """Return engine tokens that should never reach player-facing prose."""
    found = list(dict.fromkeys(_SNAKE_TOKEN.findall(prose)))
    found.extend(m.group(0) for m in _KV_TOKEN.finditer(prose))
    return found


def _mentions_participant(lower_prose: str, islander_id: str) -> bool:
    base = islander_id.lower()
    aliases = {base, base.replace("_", " ")}
    # Starting-cast ids are bare first names; Casa Amor bombshells keep an
    # "_ht" suffix (e.g. "sam_ht"). Strip any suffix segment so the first-name
    # display form the narrator actually writes is matched either way.
    aliases.add(base.split("_", 1)[0])
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
        return _player_name(state)
    for islander in state.islanders:
        if islander.id == actor_id:
            return islander.name
    return actor_id


def _player_has_name(state: GameState) -> bool:
    """True when the session set a real player name (not the "You" placeholder).

    Real play routes through the character creator, which always supplies a
    name; only quick-start sessions and placeholder checkpoints leave the
    default "You" in place.
    """
    name = (getattr(state.player, "name", "") or "").strip()
    return bool(name) and name.lower() != "you"


def _player_name(state: GameState) -> str:
    """How the narrator should refer to the human player in prose.

    When the player set a real name, the Event Narrator names them in third
    person like any other islander. When no name was set, address them in
    SECOND PERSON ("you") — consistent with the daily recap, natural for a beat
    shown to the player, and impossible to garble into a hallucinated name the
    way the old abstract label "the islander" was (gpt-5-nano once rendered it
    as "Eq stands beside Chloe").
    """
    name = (getattr(state.player, "name", "") or "").strip()
    if name and name.lower() != "you":
        return name
    return "you"


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
        f"- {event.kind}: {event.message}"
        + (f" (about {_name_for(state, event.islander_id)})" if event.islander_id else " (no named islander)")
        for event in events
    )
    named = _player_has_name(state)
    player = _player_name(state)
    if named:
        contestant_rule = (
            f"- The human contestant is named {player}; refer to them as {player} "
            '(third person), never "the player" or "you".'
        )
        possessive = f"{player}'s"
        subject = player
    else:
        contestant_rule = (
            "- The human contestant is the reader. Address them in SECOND PERSON "
            'as "you"/"your" — never invent a name for them and never refer to '
            'them in the third person: not "the player", "the islander", "the '
            'contestant", "he", "she", or "they". An event message already phrased '
            'in second person (it starts with "You ") is the contestant\'s OWN '
            'action: keep that voice — narrate it as "you" (e.g. "you and Chloe '
            'finish as the runner-up couple"), never as a third-person subject, '
            "and never reassign the choice to the partner or anyone else."
        )
        possessive = "your"
        subject = "you"
    semantics = [
        contestant_rule,
        f"- recouple_proposal rejected means the target did not accept {possessive} proposal.",
        "- npc_proposal_incoming means a pending ask, not an accepted recoupling or couple change.",
        f"- recoupling narration should name {possessive} partner when the current couple is known.",
        f"- hideaway means {subject} and the named partner leave for a private suite beat.",
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
    if named:
        contestant_voice = (
            f"Refer to the human contestant as {player} and to everyone else by "
            "the names given in the context above, all in third person."
        )
    else:
        contestant_voice = (
            "Refer to the human contestant in SECOND PERSON (\"you\"/\"your\") and "
            "to everyone else by the names given in the context above, in third "
            "person. Do not invent a name for the contestant. When an event line "
            "is the contestant's own choice (it reads \"You ...\"), narrate it as "
            "\"you\" — never \"they\", \"he\", \"she\", \"the contestant\", or "
            "\"the player\"."
        )
    sections.append("Narrate these resolved events now. If a Minigame block is "
                    "present above, ground at least one sentence in a concrete "
                    "round detail — a picked answer (quote the answer text), a "
                    "named reveal, or a chemistry pair. " + contestant_voice +
                    " Never copy an id, a snake_case key, an underscore, or "
                    "bracketed metadata into your prose — translate them into "
                    "natural language.")
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
    # Resolve every islander id to a human *name* (third person, including the
    # player). We never feed raw ids or the "id (Name)" format here: the model
    # grounds prose in this block and will copy whatever token we hand it —
    # including a leaked raw id like "sam_ht" or a doubled "Chloe (Chloe)".
    # A bare resolved name is always prose-safe.
    def _person(islander_id: str) -> str:
        if not islander_id:
            return "someone"
        name = _name_for(state, islander_id)
        # _name_for echoes the id back when no islander matches; humanize that
        # fallback so a stray id can never reach player-facing prose.
        return name if name != islander_id else _humanize(islander_id)

    participants_str = ", ".join(_person(p) for p in challenge.participants)
    lines = [
        f"Minigame: {_event_label(challenge.kind)}",
        f"  outcome: {challenge.classification}",
        f"  participants: {participants_str}",
        "  RULE: refer to people only by the names shown above. Never print an id, "
        "a snake_case key, an underscore, or bracketed metadata in your prose.",
        "  rounds:",
    ]
    for round_ in challenge.rounds:
        chosen = next((c for c in round_.choices if c.id == round_.chosen_id), None)
        correct = next((c for c in round_.choices if c.is_correct), None)
        chosen_label = repr(chosen.label) if chosen else "(no answer)"
        correct_label = repr(correct.label) if correct else "?"
        outcome = "OK" if (chosen and chosen.is_correct) else "MISS"
        round_meta = []
        # Humanize the trait/flavor key so even if the model echoes it the prose
        # reads "their drink of choice", never "drink_of_choice".
        if round_.trait_key:
            round_meta.append(f"topic \"{_humanize(round_.trait_key)}\"")
        if round_.target_id:
            round_meta.append(f"about {_person(round_.target_id)}")
        meta_str = (" (" + ", ".join(round_meta) + ")") if round_meta else ""
        lines.append(
            f"    r{round_.index + 1} [{outcome}] {round_.stem!r}{meta_str}"
        )
        lines.append(f"        chose {chosen_label}; correct was {correct_label}; points {round_.points}")
        for reveal in round_.reveals:
            payload_parts = []
            payload = reveal.payload
            # When a key carries a raw engine code (partner_guess="low") the
            # engine also supplies a display companion (partner_guess_label=
            # "audience cool on them"). Quote only the label form and drop the
            # raw one so internal enum values never reach the recap prose.
            has_label = {
                k[: -len("_label")] for k in payload if k.endswith("_label")
            }
            for k, v in payload.items():
                # Pure routing/meta keys describe engine structure, not anything
                # the narrator should surface.
                if k in {"fact_key", "direction"}:
                    continue
                # Skip the raw code when its display companion is present.
                if k in has_label:
                    continue
                if k == "observer_id" and isinstance(v, str):
                    payload_parts.append(f"observer {_person(v)}")
                else:
                    # Humanize string values too: payloads carry engine keys
                    # like trait_key="drink_of_choice" that must not leak raw.
                    value = _humanize(v) if isinstance(v, str) else v
                    display_key = k[: -len("_label")] if k.endswith("_label") else k
                    payload_parts.append(f"{_humanize(display_key)}: {value}")
            payload_summary = ", ".join(payload_parts)
            lines.append(
                f"        reveal[{reveal.kind}] about {_person(reveal.subject_id)} — {payload_summary}"
            )
    return "\n".join(lines)


def _humanize(key: str) -> str:
    """Turn a snake_case engine key into prose-safe words.

    "drink_of_choice" -> "drink of choice"; "sam_ht" -> "sam ht".
    Used so the narrator can never echo a raw key with underscores into
    player-facing prose, even when told to ground a sentence in round detail.
    """
    return str(key).replace("_", " ").strip()


def _player_couple(state: GameState) -> str:
    named = _player_has_name(state)
    player = _player_name(state)
    single = f"{player} is single" if named else "you are single"
    for couple in state.couples:
        members = {couple.partner_a_id, couple.partner_b_id}
        if "player" not in members:
            continue
        partner_id = next((member for member in members if member != "player"), None)
        if partner_id is None:
            return single
        partner = _name_for(state, partner_id)
        return f"{player} is coupled with {partner}" if named else f"you are coupled with {partner}"
    return single
