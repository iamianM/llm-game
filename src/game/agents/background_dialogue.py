"""Background Dialogue agent for NPC-NPC conversations.

Design sources:
- 09-Social-Dynamics.md: Off-screen conversations
- 07-Gossip-And-Information.md: Gossip-generating memories

Implementation rule:
This agent writes NPC-NPC dialogue only. Villa structure comes from the
Orchestrator; memory extraction comes from the Curator.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from functools import cached_property
from pathlib import Path
from typing import Literal

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
from src.game.state.models import GameState, NPCNPCConversation

BACKGROUND_DIALOGUE_MODEL = GAME_AGENT_MODEL
# Background NPC-NPC chitchat is texture, not a player-facing scene. Default
# to low reasoning effort so multiple parallel bg calls per turn don't add
# 30s of latency.
import os as _os
BACKGROUND_DIALOGUE_REASONING_EFFORT = _os.environ.get(
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
        return OpenAI()

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
                    response = self._client.responses.parse(
                        model=self._model,
                        instructions=_BACKGROUND_DIALOGUE_PROMPT_FILE.read_text(encoding="utf-8"),
                        input=context,
                        text_format=BackgroundExchange,
                        **reasoning_request_kwargs(effort=BACKGROUND_DIALOGUE_REASONING_EFFORT),
                    )
                except Exception as exc:
                    last_error = ValueError(str(exc))
                    mark_agent_trace_validation_error("background_dialogue", attempt_number, exc)
                    if attempt == 1:
                        raise
                    continue
            finally:
                end_agent_attempt(attempt_token)
            exchange = response.output_parsed
            record_agent_trace(
                agent_name="background_dialogue",
                model=self._model,
                prompt_path=BACKGROUND_DIALOGUE_PROMPT,
                response=response,
                output=exchange,
            )
            if exchange is None:
                last_error = ValueError("Background Dialogue returned no parsed BackgroundExchange")
                mark_agent_trace_validation_error("background_dialogue", attempt_number, last_error)
            else:
                try:
                    validate_background_exchange(exchange)
                    return exchange
                except ValueError as exc:
                    last_error = exc
                    mark_agent_trace_validation_error("background_dialogue", attempt_number, exc)
            if attempt == 1 and last_error is not None:
                raise last_error
        raise AssertionError("unreachable background dialogue retry state")

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
            "Recent history:",
            history or "No prior exchanges.",
            "Write one BackgroundExchange now.",
        ]
    )


def _bystanders(state: GameState, conversation: NPCNPCConversation) -> str:
    ids = [
        islander.id
        for islander in state.islanders
        if islander.id not in conversation.participants
        and not islander.eliminated
        and islander.location_id == conversation.location_id
    ]
    if state.location_id == conversation.location_id:
        ids.append("player")
    return ", ".join(ids) if ids else "none"


def _name_for(state: GameState, islander_id: str) -> str:
    for islander in state.islanders:
        if islander.id == islander_id:
            return islander.name
    return islander_id
