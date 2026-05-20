"""Islander Voice agent for single-exchange conversations."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from functools import cached_property
from pathlib import Path
from typing import Any

from openai import OpenAI

from src.game.agents.islander_voice_context import (
    Exchange,
    IslanderVoiceContext,
    build_voice_messages,
    islander_voice_context,
    new_turn_context,
    target_for_result,
)
from src.game.content.loader import load_content
from src.game.content.models import ContentIndex
from src.game.engine.rules import MechanicalResult
from src.game.state.models import GameState, Mood

ISLANDER_VOICE_MODEL = "gpt-4.1-mini"
VALID_TONES = {
    "warm",
    "flirty",
    "suspicious",
    "amused",
    "cold",
    "vulnerable",
    "playful",
    "defensive",
}
KNOWN_NAMES = {
    "Aisha",
    "Beau",
    "Blake",
    "Chloe",
    "Jordan",
    "Jules",
    "Liam",
    "Marcus",
    "Mateo",
    "Maya",
    "Nia",
    "Noor",
    "Sasha",
    "Sophie",
    "Zara",
}

IslanderVoiceFn = Callable[[GameState, MechanicalResult], Exchange]


class OpenAIIslanderVoice:
    """Single Islander Voice agent backed by the OpenAI Responses API."""

    def __init__(
        self,
        *,
        model: str = ISLANDER_VOICE_MODEL,
        content: ContentIndex | None = None,
    ) -> None:
        load_dotenv_local()
        self._model = model
        self._content = content if content is not None else load_content()

    @cached_property
    def _client(self) -> OpenAI:
        return OpenAI()

    def generate(self, state: GameState, result: MechanicalResult) -> Exchange:
        """Generate one structured exchange for a resolved mechanical result."""
        context = islander_voice_context(state, result, self._content)
        rendered = build_voice_messages(state, state.active_conversation, new_turn_context(context))
        last_error: ValueError | None = None
        for attempt in range(3):
            retry_context = rendered if last_error is None else _with_retry_message(rendered, last_error)
            exchange = self._generate_exchange(retry_context)
            try:
                validate_exchange(exchange, context)
                return exchange
            except ValueError as exc:
                last_error = exc
                if attempt == 2:
                    raise
        raise AssertionError("unreachable Islander Voice retry state")

    def _generate_exchange(self, rendered_context: Any) -> Exchange:
        """Request one parsed Exchange from the model."""
        response = self._client.responses.parse(
            model=self._model,
            instructions=Path("src/game/agents/prompts/islander_voice.md").read_text(
                encoding="utf-8"
            ),
            input=rendered_context,
            text_format=Exchange,
            max_output_tokens=320,
        )
        exchange = response.output_parsed
        if exchange is None:
            raise ValueError("Islander Voice returned no parsed Exchange")
        return exchange


def mock_islander_voice(state: GameState, result: MechanicalResult) -> Exchange:
    """Return deterministic mock dialogue for non-LLM tests and replays."""
    target = target_for_result(state, result)
    intent_label = _intent_label(result.action.intent_id)
    if result.success:
        return Exchange(
            player_dialogue=f"I wanted to say this properly, {target.name}: {intent_label}.",
            npc_dialogue="*smiles* I hear you. That actually feels good coming from you.",
            npc_tone="warm",
            npc_mood_after=Mood.HAPPY,
        )
    return Exchange(
        player_dialogue=f"I am trying to say this right, {target.name}: {intent_label}.",
        npc_dialogue="*pauses* I get what you mean, but that did not fully land for me.",
        npc_tone="defensive",
        npc_mood_after=Mood.CONTENT,
    )


def validate_exchange(exchange: Exchange, context: IslanderVoiceContext) -> None:
    """Fail loud if generated dialogue violates the exchange contract."""
    joined = f"{exchange.player_dialogue} {exchange.npc_dialogue}"
    word_count = len(joined.split())
    if not 20 <= word_count <= 150:
        raise ValueError(
            f"exchange word count out of bounds: {word_count}; exchange={exchange!r}"
        )
    if re.search(r"\d", joined):
        raise ValueError(f"exchange contains digits; exchange={exchange!r}")
    allowed = {context.npc_name, *context.others_present}
    hidden_mentions = sorted(name for name in KNOWN_NAMES - allowed if name in joined)
    if hidden_mentions:
        raise ValueError(
            f"exchange mentions hidden islander(s) {hidden_mentions}; exchange={exchange!r}"
        )
    if exchange.npc_tone not in VALID_TONES:
        raise ValueError(f"invalid npc_tone: {exchange.npc_tone}")


def load_dotenv_local(path: Path = Path(".env.local")) -> None:
    """Load local environment variables without printing secrets."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _with_retry_message(
    messages: list[dict[str, str]],
    error: ValueError,
) -> list[dict[str, str]]:
    retry = (
        "The previous Exchange failed validation. "
        f"Validation error: {error}. "
        "Return a corrected Exchange that satisfies every hard rule. "
        "Use words for numbers, do not mention hidden Islanders, and stay within the word count."
    )
    return [*messages, {"role": "user", "content": retry}]


def _intent_label(intent_id: str | None) -> str:
    from src.game.engine.intents import get_intent

    if intent_id is None:
        return "chat"
    try:
        return get_intent(intent_id).label
    except ValueError:
        return intent_id.replace("_", " ")


__all__ = [
    "Exchange",
    "IslanderVoiceContext",
    "OpenAIIslanderVoice",
    "build_voice_messages",
    "islander_voice_context",
    "load_dotenv_local",
    "mock_islander_voice",
    "new_turn_context",
    "validate_exchange",
]
