"""Heartbreaker Voice agent for single-exchange conversations."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from functools import cached_property
from pathlib import Path
from typing import Any

from openai import OpenAI

from src.game.agents.heartbreaker_voice_context import (
    Exchange,
    HeartbreakerVoiceContext,
    build_voice_messages,
    heartbreaker_voice_context,
    new_turn_context,
    recent_player_openings,
    reused_player_opening,
    target_for_result,
)
from src.game.agents.mock_dialogue import mock_exchange_fields
from src.game.agents.runtime import (
    VOICE_PROFILE,
    AgentGenerationError,
    AgentValidationError,
    begin_agent_attempt,
    build_game_client,
    end_agent_attempt,
    mark_agent_trace_generation_error,
    mark_agent_trace_validation_error,
    reasoning_request_kwargs,
    record_agent_trace,
    start_agent_call,
)
from src.game.content.loader import load_content
from src.game.content.models import ContentIndex
from src.game.engine.rules import MechanicalResult
from src.game.state.models import GameState

HEARTBREAKER_VOICE_MODEL = VOICE_PROFILE.model
HEARTBREAKER_VOICE_REASONING_EFFORT = VOICE_PROFILE.reasoning_effort
HEARTBREAKER_VOICE_PROMPT = "src/game/agents/prompts/heartbreaker_voice.md"
_HEARTBREAKER_VOICE_PROMPT_FILE = Path(__file__).parent / "prompts" / "heartbreaker_voice.md"
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

# The second resort is branded "Flush of Hearts". Match the retired source term
# with any spacing/casing so a slipped line fails validation and the
# retry regenerates with the in-world name.
_FORBIDDEN_BRAND_RE = re.compile(r"\bflush\s+amor\b", re.IGNORECASE)

HeartbreakerVoiceFn = Callable[[GameState, MechanicalResult], Exchange]


class StaleOpenerError(ValueError):
    """The generated player line reopened with an already-used opening.

    Carried through the retry loop so the re-prompt can name the offending
    opening. Unlike a contract validation failure, a stale opener never
    degrades to mock dialogue: the last structurally valid exchange is accepted
    as a best effort once retries are exhausted (a faintly repetitive real line
    still reads better than templated demo text).
    """

    def __init__(self, opening: str) -> None:
        super().__init__(f"player line reused the opening {opening!r}")
        self.opening = opening


class OpenAIHeartbreakerVoice:
    """Single Heartbreaker Voice agent backed by the OpenAI Responses API."""

    def __init__(
        self,
        *,
        model: str = HEARTBREAKER_VOICE_MODEL,
        content: ContentIndex | None = None,
    ) -> None:
        load_dotenv_local()
        self._model = model
        self._content = content if content is not None else load_content()

    @cached_property
    def _client(self) -> OpenAI:
        return build_game_client()

    def generate(self, state: GameState, result: MechanicalResult) -> Exchange:
        """Generate one structured exchange for a resolved mechanical result."""
        context = heartbreaker_voice_context(state, result, self._content)
        rendered = build_voice_messages(state, state.active_conversation, new_turn_context(context))
        used_openings = recent_player_openings(
            state.active_conversation, state.recent_player_lines
        )
        last_error: ValueError | None = None
        # Last structurally valid exchange, kept so a stubborn opener repeat is
        # accepted as a best effort instead of falling back to mock dialogue.
        best_effort: Exchange | None = None
        for attempt in range(3):
            attempt_number = attempt + 1
            retry_context = rendered if last_error is None else _with_retry_message(rendered, last_error)
            attempt_token = begin_agent_attempt(attempt_number)
            try:
                try:
                    exchange = self._generate_exchange(retry_context)
                except Exception as exc:
                    mark_agent_trace_generation_error("heartbreaker_voice", attempt_number, exc)
                    last_error = ValueError(str(exc))
                    if attempt == 2:
                        raise AgentGenerationError(str(exc)) from exc
                    continue
            finally:
                end_agent_attempt(attempt_token)
            try:
                validate_exchange(exchange, context)
            except ValueError as exc:
                mark_agent_trace_validation_error("heartbreaker_voice", attempt_number, exc)
                last_error = exc
                if attempt == 2:
                    raise AgentValidationError(str(exc)) from exc
                continue
            # Structurally valid. Prefer a fresh opener, but never hard-fail on
            # repetition: redraw once or twice, then take the best effort.
            best_effort = exchange
            collision = reused_player_opening(exchange.player_dialogue, used_openings)
            if collision is not None and attempt < 2:
                last_error = StaleOpenerError(collision)
                continue
            return exchange
        if best_effort is not None:
            return best_effort
        raise AssertionError("unreachable Heartbreaker Voice retry state")

    def _generate_exchange(self, rendered_context: Any) -> Exchange:
        """Request one parsed Exchange from the model."""
        instructions = _HEARTBREAKER_VOICE_PROMPT_FILE.read_text(encoding="utf-8")
        started_at = start_agent_call()
        response = self._client.responses.parse(
            model=self._model,
            instructions=instructions,
            input=rendered_context,
            text_format=Exchange,
            **reasoning_request_kwargs(effort=HEARTBREAKER_VOICE_REASONING_EFFORT),
        )
        exchange = response.output_parsed
        record_agent_trace(
            agent_name="heartbreaker_voice",
            model=self._model,
            prompt_path=HEARTBREAKER_VOICE_PROMPT,
            response=response,
            output=exchange,
            reasoning_effort=HEARTBREAKER_VOICE_REASONING_EFFORT,
            prompt_text=instructions,
            input_payload=rendered_context,
            started_at=started_at,
        )
        if exchange is None:
            raise ValueError("Heartbreaker Voice returned no parsed Exchange")
        return exchange


def mock_heartbreaker_voice(state: GameState, result: MechanicalResult) -> Exchange:
    """Return deterministic, in-character demo dialogue for non-LLM play.

    Demo mode is the default in the browser when no LLM key is configured, so
    these lines are the first conversation most players see. They are keyed by
    intent category (flirty / deep / banter / ...) and rotate phrasing on the
    deterministic dice roll, so the experience reads like real dialogue while
    staying fully replayable.
    """
    target = target_for_result(state, result)
    player, npc, tone, mood = mock_exchange_fields(
        category=_intent_category(result.action.intent_id),
        success=result.success,
        target_name=target.name,
        roll=result.roll,
    )
    return Exchange(
        player_dialogue=player,
        npc_dialogue=npc,
        npc_tone=tone,
        npc_mood_after=mood,
    )


def _intent_category(intent_id: str | None) -> str | None:
    """Resolve an intent id to its dialogue category, or None.

    Tries the main intent catalog first (menu leaf intents such as
    ``compliment_looks``), then the follow-up option registry (conversation
    wheel responses such as ``joke_back`` / ``escalate_flirt`` that are not
    catalog intents). Resolving follow-ups too keeps multi-turn demo
    conversations varied instead of repeatedly falling back to the default
    opener lines. Imports are local to avoid an import cycle: ``option_defaults``
    imports ``Exchange`` from this module.
    """
    if not intent_id:
        return None
    from src.game.engine.intents import get_intent

    try:
        return get_intent(intent_id).category.value
    except ValueError:
        pass
    from src.game.engine.option_defaults import OPTION_TEMPLATES

    option = OPTION_TEMPLATES.get(intent_id)
    return option.category if option is not None else None


def validate_exchange(exchange: Exchange, context: HeartbreakerVoiceContext) -> None:
    """Fail loud if generated dialogue violates the agent boundary.

    Only enforces the structural contract: dialogue must not mention an
    Heartbreaker who is not present and not a legal gossip subject. Length, tone
    of voice, and digit-vs-spelled-number preferences are conveyed via the
    prompt, not enforced here.
    """
    joined = f"{exchange.player_dialogue} {exchange.npc_dialogue}"
    allowed = {context.npc_name, *context.others_present, *context.gossip_subject_names}
    cast = set(context.cast_names)
    hidden_mentions = sorted(
        name
        for name in cast - allowed
        if re.search(rf"\b{re.escape(name)}\b", joined)
    )
    if hidden_mentions:
        raise ValueError(
            f"exchange mentions hidden heartbreaker(s) {hidden_mentions}; exchange={exchange!r}"
        )
    # In-world vocabulary: the second resort is branded "Flush of Hearts". nano
    # occasionally slips into source-show vocabulary, which breaks the fiction. Fail loud so
    # the retry regenerates with the branded name rather than scrubbing it
    # downstream (ENGINEERING R7 — keep the agent boundary honest).
    if _FORBIDDEN_BRAND_RE.search(joined):
        raise ValueError(
            "exchange uses the retired source-show term; the second resort is "
            f'the "Flush of Hearts". exchange={exchange!r}'
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
    if isinstance(error, StaleOpenerError):
        retry = (
            f'Your player line opened with "{error.opening}", which the player '
            "already used recently. Rewrite the player line so it BEGINS with a "
            "different phrase and a different move — not another greeting or "
            '"you don\'t have to have it all figured out" style reassurance frame. '
            "Keep the same intent, warmth, and length; only vary how it opens. "
            "Return the full corrected Exchange."
        )
    else:
        retry = (
            "The previous Exchange failed validation. "
            f"Validation error: {error}. "
            "Return a corrected Exchange that satisfies every hard rule. "
            "Use words for numbers, do not mention hidden Heartbreakers, and stay within the word count."
        )
    return [*messages, {"role": "user", "content": retry}]


__all__ = [
    "Exchange",
    "HeartbreakerVoiceContext",
    "OpenAIHeartbreakerVoice",
    "StaleOpenerError",
    "build_voice_messages",
    "heartbreaker_voice_context",
    "load_dotenv_local",
    "mock_heartbreaker_voice",
    "new_turn_context",
    "validate_exchange",
]
