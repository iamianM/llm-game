"""Narration agents for Blackfen Road."""

from __future__ import annotations

import re
from functools import cached_property
from pathlib import Path
from typing import Protocol

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, ValidationError

from src.blackfen.content import load_world
from src.blackfen.models import GameState, MechanicalResult, RunStatus
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

BLACKFEN_NARRATOR_MODEL = GAME_AGENT_MODEL
BLACKFEN_NARRATOR_PROMPT = "src/blackfen/agents/prompts/narrator.md"
_BLACKFEN_NARRATOR_PROMPT_FILE = Path(__file__).parent / "prompts" / "narrator.md"


class Narrator(Protocol):
    """Render a resolved mechanical result as player-facing prose."""

    def narrate(self, state: GameState, result: MechanicalResult) -> str:
        """Return narration for an already-resolved turn."""


class MockNarrator:
    """Deterministic narrator for tests and offline play."""

    def narrate(self, state: GameState, result: MechanicalResult) -> str:
        world = load_world()
        location = world.locations[state.current_location_id]
        lines = [result.summary]
        lines.extend(result.details)
        if result.discovered_locations:
            names = [world.locations[id_].name for id_ in result.discovered_locations]
            lines.append("New leads: " + ", ".join(names) + ".")
        if result.items_gained:
            names = [world.items[id_].name for id_ in result.items_gained]
            lines.append("You gain: " + ", ".join(names) + ".")
        if state.status is RunStatus.DEAD:
            lines.append("Your road ends in Blackfen. The next traveler may find what you left behind.")
        elif state.status is RunStatus.VICTORY:
            lines.append("The drowned bell falls silent. Blackfen will remember your name.")
        else:
            lines.append(f"You are at {location.name}. {location.description}")
        return "\n".join(lines)


class NarrationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    narration: str


class OpenAINarrator:
    """Live Dungeon Master narration backed by OpenAI Responses."""

    def __init__(self, *, model: str = BLACKFEN_NARRATOR_MODEL) -> None:
        load_dotenv_local()
        self._model = model

    @cached_property
    def _client(self) -> OpenAI:
        return build_game_client()

    def narrate(self, state: GameState, result: MechanicalResult) -> str:
        rendered = _render_narration_context(state, result)
        last_error: ValueError | None = None
        for attempt in range(3):
            attempt_number = attempt + 1
            retry_context = rendered
            if last_error is not None:
                retry_context = (
                    f"{rendered}\n\nPrevious narration failed validation: {last_error}. "
                    "Rewrite it as clean player-facing prose without engine tokens."
                )
            attempt_token = begin_agent_attempt(attempt_number)
            try:
                try:
                    output = self._generate(retry_context)
                    _validate_narration(output.narration)
                    return output.narration
                except Exception as exc:
                    mark_agent_trace_validation_error("blackfen_narrator", attempt_number, exc, prompt_path=BLACKFEN_NARRATOR_PROMPT)
                    last_error = ValueError(str(exc))
                    if attempt == 2:
                        if isinstance(exc, (ValueError, ValidationError)):
                            raise AgentValidationError(str(exc)) from exc
                        raise AgentGenerationError(str(exc)) from exc
            finally:
                end_agent_attempt(attempt_token)
        raise AssertionError("unreachable Blackfen narrator retry state")

    def _generate(self, rendered_context: str) -> NarrationOutput:
        response = self._client.responses.parse(
            model=self._model,
            instructions=_BLACKFEN_NARRATOR_PROMPT_FILE.read_text(encoding="utf-8"),
            input=rendered_context,
            text_format=NarrationOutput,
            **reasoning_request_kwargs(),
        )
        output = response.output_parsed
        record_agent_trace(
            agent_name="blackfen_narrator",
            model=self._model,
            prompt_path=BLACKFEN_NARRATOR_PROMPT,
            response=response,
            output=output,
        )
        if output is None:
            raise ValueError("Blackfen narrator returned no parsed output")
        return output


def _render_narration_context(state: GameState, result: MechanicalResult) -> str:
    world = load_world()
    location = world.locations[state.current_location_id]
    monsters: list[str] = []
    if location.encounter is not None:
        for monster in state.active_monsters.get(location.encounter, []):
            monster_def = world.monsters[monster.id]
            monsters.append(f"{monster_def.name} HP {monster.hp}")
    return "\n".join(
        [
            f"Player: {state.player.name}, HP {state.player.hp}/{state.player.max_hp}, AC {state.player.armor_class}",
            f"Companion: {state.companion.name}, HP {state.companion.hp}/{state.companion.max_hp}, stance {state.companion.stance}",
            f"Location: {location.name} ({location.kind})",
            f"Location description: {location.description}",
            f"Visible threats: {', '.join(monsters) or 'none'}",
            f"Player input: {result.intent.raw_text}",
            f"Resolved intent: {result.intent.kind.value}",
            f"Mechanical summary: {result.summary}",
            f"Mechanical details: {' | '.join(result.details) or 'none'}",
            f"Rolls: {' | '.join(f'{roll.label} total {roll.total} target {roll.target}' for roll in result.rolls) or 'none'}",
            f"Damage: player {result.damage_to_player}, companion {result.damage_to_companion}, enemies {result.damage_to_enemies}",
            f"Discovered locations: {', '.join(world.locations[id_].name for id_ in result.discovered_locations) or 'none'}",
            f"Items gained: {', '.join(world.items[id_].name for id_ in result.items_gained) or 'none'}",
            f"Items lost: {', '.join(world.items[id_].name for id_ in result.items_lost) or 'none'}",
            f"Run status: {state.status.value}",
            "Narrate only this resolved result.",
        ]
    )


_ENGINE_TOKEN = re.compile(r"\b[a-z0-9]+(?:_[a-z0-9]+)+\b|\b(?:target_id|run_status|mechanical_result|raw_text)\b")


def _validate_narration(narration: str) -> None:
    if not narration.strip():
        raise ValueError("narration is empty")
    leaked = _ENGINE_TOKEN.findall(narration)
    if leaked:
        raise ValueError(f"narration leaked engine token(s): {sorted(set(leaked))}")
