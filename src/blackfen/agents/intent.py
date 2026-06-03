"""Intent parsing agents for freeform Blackfen Road input."""

from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Protocol

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, ValidationError

from src.blackfen.content import load_world
from src.blackfen.models import GameState, Intent, IntentKind
from src.game.agents.heartbreaker_voice import load_dotenv_local
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

BLACKFEN_INTENT_MODEL = GAME_AGENT_MODEL
BLACKFEN_INTENT_PROMPT = "src/blackfen/agents/prompts/intent_parser.md"
_BLACKFEN_INTENT_PROMPT_FILE = Path(__file__).parent / "prompts" / "intent_parser.md"


class IntentParseOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: IntentKind
    raw_text: str
    target_id: str | None = None
    approach: str | None = None


class IntentParser(Protocol):
    """Convert freeform player input into a typed engine intent."""

    def parse(self, state: GameState, text: str) -> Intent:
        """Return a typed intent for the current state."""


class LocalIntentParser:
    """Deterministic parser used by CLI tests, mock API runs, and offline play."""

    def parse(self, state: GameState, text: str) -> Intent:
        raw = text.strip()
        if not raw:
            raise ValueError("enter an action")
        lowered = raw.lower()
        world = load_world()
        visible_locations = [world.locations[id_] for id_ in state.known_locations]
        for location in visible_locations:
            names = {location.id.replace("_", " "), location.name.lower()}
            if any(name in lowered for name in names) and _has_travel_verb(lowered):
                return Intent(kind=IntentKind.TRAVEL, raw_text=raw, target_id=location.id)
        current = world.locations[state.current_location_id]
        for exit_id in current.exits:
            location = world.locations[exit_id]
            if location.name.lower() in lowered or exit_id.replace("_", " ") in lowered:
                return Intent(kind=IntentKind.TRAVEL, raw_text=raw, target_id=exit_id)
        for npc_id in current.npcs:
            npc = world.npcs[npc_id]
            if npc.name.lower() in lowered or npc.role.lower() in lowered:
                return Intent(kind=IntentKind.TALK, raw_text=raw, target_id=npc_id)
        if any(word in lowered for word in ("attack", "fight", "shoot", "stab", "strike", "kill")):
            return Intent(kind=IntentKind.ATTACK, raw_text=raw)
        if any(word in lowered for word in ("rest", "sleep", "camp", "recover")):
            return Intent(kind=IntentKind.REST, raw_text=raw)
        if any(word in lowered for word in ("potion", "drink", "use")):
            return Intent(kind=IntentKind.USE_ITEM, raw_text=raw, target_id="healing_potion")
        if "elian" in lowered or "companion" in lowered:
            return Intent(kind=IntentKind.COMMAND_COMPANION, raw_text=raw, approach=raw)
        if any(word in lowered for word in ("look", "search", "inspect", "investigate", "track", "listen", "read")):
            return Intent(kind=IntentKind.INSPECT, raw_text=raw)
        if any(word in lowered for word in ("talk", "ask", "speak", "question")) and current.npcs:
            return Intent(kind=IntentKind.TALK, raw_text=raw, target_id=current.npcs[0])
        return Intent(kind=IntentKind.INSPECT, raw_text=raw, approach="fallback_inspect")


def _has_travel_verb(text: str) -> bool:
    return any(word in text for word in ("go", "walk", "travel", "head", "leave", "enter", "follow"))


class OpenAIIntentParser:
    """Live freeform intent parser backed by OpenAI Responses."""

    def __init__(self, *, model: str = BLACKFEN_INTENT_MODEL) -> None:
        load_dotenv_local()
        self._model = model

    @cached_property
    def _client(self) -> OpenAI:
        return build_game_client()

    def parse(self, state: GameState, text: str) -> Intent:
        raw = text.strip()
        if not raw:
            raise ValueError("enter an action")
        rendered = _render_intent_context(state, raw)
        last_error: ValueError | None = None
        for attempt in range(3):
            attempt_number = attempt + 1
            retry_context = rendered
            if last_error is not None:
                retry_context = (
                    f"{rendered}\n\nPrevious output failed validation: {last_error}. "
                    "Return a corrected intent using only the allowed target ids."
                )
            attempt_token = begin_agent_attempt(attempt_number)
            try:
                try:
                    output = self._generate(retry_context)
                    intent = Intent(raw_text=raw, kind=output.kind, target_id=output.target_id, approach=output.approach)
                    _validate_live_intent(state, intent)
                    return intent
                except Exception as exc:
                    mark_agent_trace_validation_error("blackfen_intent_parser", attempt_number, exc, prompt_path=BLACKFEN_INTENT_PROMPT)
                    last_error = ValueError(str(exc))
                    if attempt == 2:
                        if isinstance(exc, (ValueError, ValidationError)):
                            raise AgentValidationError(str(exc)) from exc
                        raise AgentGenerationError(str(exc)) from exc
            finally:
                end_agent_attempt(attempt_token)
        raise AssertionError("unreachable Blackfen intent retry state")

    def _generate(self, rendered_context: str) -> IntentParseOutput:
        response = self._client.responses.parse(
            model=self._model,
            instructions=_BLACKFEN_INTENT_PROMPT_FILE.read_text(encoding="utf-8"),
            input=rendered_context,
            text_format=IntentParseOutput,
            **reasoning_request_kwargs(),
        )
        output = response.output_parsed
        record_agent_trace(
            agent_name="blackfen_intent_parser",
            model=self._model,
            prompt_path=BLACKFEN_INTENT_PROMPT,
            response=response,
            output=output,
        )
        if output is None:
            raise ValueError("Blackfen intent parser returned no parsed output")
        return output


def _render_intent_context(state: GameState, raw_text: str) -> str:
    world = load_world()
    location = world.locations[state.current_location_id]
    known_locations = [world.locations[id_] for id_ in state.known_locations]
    visible_targets = [f"- location {loc.id}: {loc.name}" for loc in known_locations]
    visible_targets.extend(f"- npc {npc_id}: {world.npcs[npc_id].name}, {world.npcs[npc_id].role}" for npc_id in location.npcs)
    if location.encounter is not None:
        for monster in state.active_monsters.get(location.encounter, []):
            monster_def = world.monsters[monster.id]
            visible_targets.append(f"- monster {monster.instance_id}: {monster_def.name}")
    visible_targets.extend(f"- item {item_id}: {world.items[item_id].name}" for item_id in state.player.inventory)
    return "\n".join(
        [
            f"Player text: {raw_text}",
            f"Current location: {location.id} ({location.name})",
            f"Connected exits: {', '.join(location.exits) or 'none'}",
            "Allowed targets:",
            *visible_targets,
            "Action vocabulary: travel, inspect, talk, attack, rest, use_item, command_companion.",
        ]
    )


def _validate_live_intent(state: GameState, intent: Intent) -> None:
    world = load_world()
    location = world.locations[state.current_location_id]
    allowed_targets = set(state.known_locations)
    allowed_targets.update(location.exits)
    allowed_targets.update(location.npcs)
    allowed_targets.update(state.player.inventory)
    if location.encounter is not None:
        allowed_targets.update(monster.instance_id for monster in state.active_monsters.get(location.encounter, []))
    if intent.target_id is not None and intent.target_id not in allowed_targets:
        raise ValueError(f"target_id {intent.target_id!r} is not currently allowed")
    if intent.kind is IntentKind.TRAVEL and intent.target_id is None:
        raise ValueError("travel requires a target_id")
    if intent.kind is IntentKind.TALK and intent.target_id is not None and intent.target_id not in location.npcs:
        raise ValueError("talk target must be an NPC at the current location")
