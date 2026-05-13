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
from src.game.state.models import GameState, NPCNPCConversation

BACKGROUND_DIALOGUE_MODEL = "gpt-4.1-nano"


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
            context = rendered
            if last_error is not None:
                context = (
                    f"{rendered}\n\nPrevious BackgroundExchange failed validation: "
                    f"{last_error}. Return a corrected BackgroundExchange."
                )
            response = self._client.responses.parse(
                model=self._model,
                instructions=Path("src/game/agents/prompts/background_dialogue.md").read_text(
                    encoding="utf-8"
                ),
                input=context,
                text_format=BackgroundExchange,
                max_output_tokens=320,
            )
            exchange = response.output_parsed
            if exchange is None:
                last_error = ValueError("Background Dialogue returned no parsed BackgroundExchange")
            else:
                try:
                    validate_background_exchange(exchange)
                    return exchange
                except ValueError as exc:
                    last_error = exc
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
    """Fail loud if generated background dialogue violates contract."""
    joined = f"{exchange.speaker_a_line} {exchange.speaker_b_line}"
    word_count = len(joined.split())
    if not 20 <= word_count <= 120:
        raise ValueError(f"background exchange word count out of bounds: {word_count}")
    if re.search(r"\d", joined):
        raise ValueError(f"background exchange contains digits: {exchange!r}")
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
        for exchange in conversation.exchanges[-4:]
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
