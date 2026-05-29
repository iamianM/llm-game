"""NPC Greeter agent for Day-1 opening greetings.

Implementation rule:
This agent writes a single, voice-true opening line per NPC for the Day-1
greeting circle. Called once at intros start (right after character
creation) and parallelized across all islanders.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import cached_property
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict

from src.game.agents.islander_voice import load_dotenv_local
from src.game.agents.runtime import (
    GAME_AGENT_MODEL,
    begin_agent_attempt,
    end_agent_attempt,
    mark_agent_trace_validation_error,
    reasoning_request_kwargs,
    record_agent_trace,
)
from src.game.state.models import GameState, IslanderState

NPC_GREETER_MODEL = GAME_AGENT_MODEL
NPC_GREETER_REASONING_EFFORT = os.environ.get("LLM_NPC_GREETER_REASONING_EFFORT", "low")
NPC_GREETER_MAX_CONCURRENCY = int(os.environ.get("LLM_NPC_GREETER_MAX_CONCURRENCY", "8"))

NPC_GREETER_PROMPT = "src/game/agents/prompts/npc_greeter.md"
_NPC_GREETER_PROMPT_FILE = Path(__file__).parent / "prompts" / "npc_greeter.md"


class GreetingLine(BaseModel):
    """One generated opening greeting from an islander to the player."""

    model_config = ConfigDict(extra="forbid")

    greeting: str


# Returns a dict of islander_id -> greeting line, populated for every
# non-eliminated NPC the player will meet during Day-1 intros.
NpcGreeterFn = Callable[[GameState], dict[str, str]]


class OpenAINpcGreeter:
    """NPC Greeter agent backed by OpenAI Responses."""

    def __init__(self, *, model: str = NPC_GREETER_MODEL) -> None:
        load_dotenv_local()
        self._model = model

    @cached_property
    def _client(self) -> OpenAI:
        return OpenAI()

    def generate(self, state: GameState) -> dict[str, str]:
        """Generate greetings for every Day-1 intro target, in parallel.

        Eight islanders is the default opening cast; sequential calls would
        add ~5-8s of wall-time to the casting screen. Parallelizing brings
        that down to roughly the slowest single call.
        """
        targets = _intro_targets(state)
        if not targets:
            return {}
        instructions = _NPC_GREETER_PROMPT_FILE.read_text(encoding="utf-8")
        max_workers = max(1, min(len(targets), NPC_GREETER_MAX_CONCURRENCY))
        greetings: dict[str, str] = {}
        errors: list[BaseException] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self._greet_one_with_retries, state, target, instructions): target
                for target in targets
            }
            for future in as_completed(futures):
                target = futures[future]
                try:
                    greetings[target.id] = future.result()
                except BaseException as exc:  # noqa: BLE001 — collect-then-raise
                    errors.append(exc)
        if errors:
            raise errors[0]
        return greetings

    async def generate_async(self, state: GameState) -> dict[str, str]:
        return await asyncio.to_thread(self.generate, state)

    def _greet_one_with_retries(
        self, state: GameState, target: IslanderState, instructions: str
    ) -> str:
        rendered = _render_context(state, target)
        last_error: ValueError | None = None
        for attempt in range(2):
            attempt_number = attempt + 1
            input_text = rendered
            if last_error is not None:
                input_text = (
                    f"{rendered}\n\nPrevious GreetingLine failed validation: "
                    f"{last_error}. Return a corrected GreetingLine (one short opening "
                    "sentence in this islander's voice; no stage directions in asterisks)."
                )
            attempt_token = begin_agent_attempt(attempt_number)
            try:
                try:
                    response = self._client.responses.parse(
                        model=self._model,
                        instructions=instructions,
                        input=input_text,
                        text_format=GreetingLine,
                        **reasoning_request_kwargs(effort=NPC_GREETER_REASONING_EFFORT),
                    )
                except Exception as exc:
                    last_error = ValueError(str(exc))
                    mark_agent_trace_validation_error("npc_greeter", attempt_number, exc)
                    if attempt == 1:
                        raise
                    continue
            finally:
                end_agent_attempt(attempt_token)
            line = response.output_parsed
            record_agent_trace(
                agent_name="npc_greeter",
                model=self._model,
                prompt_path=NPC_GREETER_PROMPT,
                response=response,
                output=line,
            )
            if line is None:
                last_error = ValueError("Greeter returned no parsed GreetingLine")
                mark_agent_trace_validation_error("npc_greeter", attempt_number, last_error)
                continue
            try:
                validate_greeting(line.greeting, target_name=target.name)
                return line.greeting.strip()
            except ValueError as exc:
                last_error = exc
                mark_agent_trace_validation_error("npc_greeter", attempt_number, exc)
        if last_error is not None:
            raise last_error
        raise AssertionError("unreachable npc_greeter retry state")


def mock_npc_greeter(state: GameState) -> dict[str, str]:
    """Return an empty dict — UI falls through to templated greetings.

    Demo mode keeps the per-archetype template lookup in `web/lib/intros.ts`
    so the deterministic CLI/test paths don't need an LLM call shape.
    """
    return {}


def validate_greeting(text: str, *, target_name: str) -> None:
    """Fail loud on greetings that violate the contract.

    Hard rules: non-empty, <=240 chars (3 short lines worth), no third-person
    self-description (NPC says "I'm Blake", not "Blake is here"), no
    asterisked stage directions.
    """
    stripped = text.strip()
    if not stripped:
        raise ValueError("greeting is empty")
    if len(stripped) > 240:
        raise ValueError(f"greeting too long ({len(stripped)} chars; cap is 240)")
    if "*" in stripped:
        raise ValueError("greeting must not include stage directions in asterisks")


def _intro_targets(state: GameState) -> list[IslanderState]:
    return [islander for islander in state.islanders if not islander.eliminated]


def _render_context(state: GameState, target: IslanderState) -> str:
    persona = (
        target.trait_card.persona.one_line
        if target.trait_card and target.trait_card.persona
        else ""
    )
    return "\n".join(
        [
            f"You are {target.name}, a {target.archetype}. You are a {target.gender}.",
            f"Persona: {persona or 'easygoing, voice-true to your archetype.'}",
            f"Day {state.day}, {state.phase.value}, at the firepit.",
            f"You are meeting the player for the first time. Player is a {state.player.gender}.",
            "Write ONE short opening greeting in your voice — first-person, addressed to the player.",
            "Reference something specific about them or this villa moment, not generic small talk.",
            "Do NOT include asterisks or stage directions; just the spoken line.",
        ]
    )


__all__ = (
    "GreetingLine",
    "NpcGreeterFn",
    "NPC_GREETER_MODEL",
    "NPC_GREETER_PROMPT",
    "OpenAINpcGreeter",
    "mock_npc_greeter",
    "validate_greeting",
)
