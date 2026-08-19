"""Background Dialogue agent for NPC-NPC conversations.

Design sources:
- docs/design/09-Social-Dynamics.md: Off-screen conversations
- docs/design/07-Gossip-And-Information.md: Gossip-generating memories

Implementation rule:
This agent writes NPC-NPC dialogue only. Resort structure comes from the
Orchestrator; memory extraction comes from the Curator.
"""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Callable
from functools import cached_property
from pathlib import Path
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict

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
from src.game.state.models import GameState, Gender, NPCNPCConversation

BACKGROUND_DIALOGUE_MODEL = GAME_AGENT_MODEL
# Background NPC-NPC chitchat is texture, not a player-facing scene. Default
# to low reasoning effort so multiple parallel bg calls per turn don't add
# 30s of latency.
BACKGROUND_DIALOGUE_REASONING_EFFORT = os.environ.get(
    "LLM_BACKGROUND_DIALOGUE_REASONING_EFFORT", "low"
)
BACKGROUND_DIALOGUE_PROMPT = "src/game/agents/prompts/background_dialogue.md"
_BACKGROUND_DIALOGUE_PROMPT_FILE = Path(__file__).parent / "prompts" / "background_dialogue.md"


class BackgroundExchange(BaseModel):
    """One generated NPC-NPC exchange."""

    model_config = ConfigDict(extra="forbid")

    speaker_a_line: str
    speaker_b_line: str
    tone: Literal[
        "warm",
        "flirty",
        "tense",
        "playful",
        "cold",
        "vulnerable",
        "gossipy",
        "competitive",
        "intimate",
    ]


BackgroundDialogueFn = Callable[[GameState, NPCNPCConversation, str], BackgroundExchange]


class OpenAIBackgroundDialogue:
    """Background Dialogue agent backed by OpenAI Responses."""

    def __init__(self, *, model: str = BACKGROUND_DIALOGUE_MODEL) -> None:
        load_dotenv_local()
        self._model = model

    @cached_property
    def _client(self) -> OpenAI:
        return build_game_client()

    def generate(
        self,
        state: GameState,
        conversation: NPCNPCConversation,
        nudge: str = "",
    ) -> BackgroundExchange:
        """Generate and validate one NPC-NPC exchange."""
        rendered = _render_context(state, conversation, nudge)
        last_error: ValueError | None = None
        for attempt in range(2):
            attempt_number = attempt + 1
            context = rendered
            if last_error is not None:
                context = (
                    f"{rendered}\n\nPrevious BackgroundExchange failed validation: "
                    f"{last_error}. Return a corrected BackgroundExchange."
                )
            attempt_token = begin_agent_attempt(attempt_number)
            try:
                try:
                    exchange = self._generate_exchange(context)
                except Exception as exc:
                    mark_agent_trace_validation_error("background_dialogue", attempt_number, exc)
                    last_error = ValueError(str(exc))
                    if attempt == 1:
                        raise AgentGenerationError(str(exc)) from exc
                    continue
            finally:
                end_agent_attempt(attempt_token)
            try:
                validate_background_exchange(exchange)
                return exchange
            except ValueError as exc:
                mark_agent_trace_validation_error("background_dialogue", attempt_number, exc)
                last_error = exc
                if attempt == 1:
                    raise AgentValidationError(str(exc)) from exc
        raise AssertionError("unreachable background dialogue retry state")

    def _generate_exchange(self, rendered_context: str) -> BackgroundExchange:
        """Request one parsed BackgroundExchange from the model."""
        response = self._client.responses.parse(
            model=self._model,
            instructions=_BACKGROUND_DIALOGUE_PROMPT_FILE.read_text(encoding="utf-8"),
            input=rendered_context,
            text_format=BackgroundExchange,
            **reasoning_request_kwargs(effort=BACKGROUND_DIALOGUE_REASONING_EFFORT),
        )
        exchange = response.output_parsed
        record_agent_trace(
            agent_name="background_dialogue",
            model=self._model,
            prompt_path=BACKGROUND_DIALOGUE_PROMPT,
            response=response,
            output=exchange,
        )
        if exchange is None:
            raise ValueError("Background Dialogue returned no parsed BackgroundExchange")
        return exchange

    async def generate_async(
        self,
        state: GameState,
        conversation: NPCNPCConversation,
        nudge: str = "",
    ) -> BackgroundExchange:
        """Generate one NPC-NPC exchange without blocking sibling background calls."""
        return await asyncio.to_thread(self.generate, state, conversation, nudge)


def mock_background_dialogue(
    state: GameState,
    conversation: NPCNPCConversation,
    nudge: str = "",
) -> BackgroundExchange:
    """Return deterministic NPC-NPC dialogue for offline tests."""
    first_id, second_id = conversation.participants
    first = _name_for(state, first_id)
    second = _name_for(state, second_id)
    topic = nudge or conversation.topic
    return BackgroundExchange(
        speaker_a_line=f"*glances over* {second}, this {topic} thing is sticking with me.",
        speaker_b_line=f"*nods* I know, {first}. It feels like everyone can sense it.",
        tone="gossipy",
    )


def validate_background_exchange(exchange: BackgroundExchange) -> None:
    """Fail loud if generated background dialogue violates the agent boundary.

    Only enforces the third-person body language contract — speakers describe
    each other, not themselves. Length and digit-vs-spelled-number
    preferences are conveyed via the prompt, not enforced here.
    """
    joined = f"{exchange.speaker_a_line} {exchange.speaker_b_line}"
    body_language = " ".join(re.findall(r"\*([^*]+)\*", joined))
    if re.search(r"\bmy (lips|eyes|hands|shoulder|arm|face)\b", body_language, re.IGNORECASE):
        raise ValueError(f"background exchange uses first-person body language: {exchange!r}")


def _render_context(state: GameState, conversation: NPCNPCConversation, nudge: str) -> str:
    first_id, second_id = conversation.participants
    history = "\n".join(
        (
            f"- {exchange.speaker_a_id}: {exchange.speaker_a_line}; "
            f"{exchange.speaker_b_id}: {exchange.speaker_b_line}; tone {exchange.tone}"
        )
        for exchange in conversation.exchanges
    )
    return "\n".join(
        [
            f"Day: {state.day}",
            f"Phase: {state.phase.value}",
            f"Location: {conversation.location_id.value}",
            f"Topic: {conversation.topic}",
            f"Nudge: {nudge or 'none'}",
            f"Speaker A: {first_id} ({_name_for(state, first_id)})",
            f"Speaker B: {second_id} ({_name_for(state, second_id)})",
            f"Bystanders: {_bystanders(state, conversation)}",
            "Cast pronouns (use exactly these — never guess gender from a name): "
            f"{_cast_pronouns(state)}",
            "Recent history:",
            history or "No prior exchanges.",
            "Write one BackgroundExchange now.",
        ]
    )


def _bystanders(state: GameState, conversation: NPCNPCConversation) -> str:
    ids = [
        heartbreaker.id
        for heartbreaker in state.heartbreakers
        if heartbreaker.id not in conversation.participants
        and not heartbreaker.eliminated
        and heartbreaker.location_id == conversation.location_id
    ]
    if state.location_id == conversation.location_id:
        ids.append("player")
    return ", ".join(ids) if ids else "none"


def _name_for(state: GameState, heartbreaker_id: str) -> str:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == heartbreaker_id:
            return heartbreaker.name
    return heartbreaker_id


def _cast_pronouns(state: GameState) -> str:
    """`Name: pronouns` for every living heartbreaker.

    The two speakers — or a bystander they react to — may be unisex-named
    (Jules, Sam, Riley, Noor), so the name alone does not reveal gender. This
    roster lets the background voice pick the right pronoun instead of guessing.
    """
    lines = [
        f"{heartbreaker.name}: {'she/her' if heartbreaker.gender == Gender.WOMAN else 'he/him'}"
        for heartbreaker in state.heartbreakers
        if not heartbreaker.eliminated
    ]
    return ", ".join(lines) if lines else "none"
