"""Shared live-agent model settings and trace capture."""

from __future__ import annotations

import os
from contextvars import ContextVar, Token
from dataclasses import dataclass
from hashlib import sha256
from time import perf_counter
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

# Role profiles make latency/quality experiments explicit without changing the
# game context or maintaining a second agent path. A single base override still
# provides a convenient whole-pack experiment.
GAME_AGENT_MODEL = os.environ.get("LLM_GAME_MODEL", "gpt-5.6-luna")
GAME_AGENT_REASONING_EFFORT = os.environ.get("LLM_GAME_REASONING_EFFORT", "low")
GAME_AGENT_REASONING_SUMMARY = os.environ.get("LLM_GAME_REASONING_SUMMARY", "detailed")
GAME_AGENT_RESPONSE_INCLUDE = ["reasoning.encrypted_content"]


@dataclass(frozen=True)
class AgentModelProfile:
    """Model and reasoning defaults for one class of agent work."""

    role: str
    model: str
    reasoning_effort: str


def _profile(role: str, default_effort: str) -> AgentModelProfile:
    env_role = role.upper()
    return AgentModelProfile(
        role=role,
        model=os.environ.get(f"LLM_GAME_{env_role}_MODEL", GAME_AGENT_MODEL),
        reasoning_effort=os.environ.get(
            f"LLM_GAME_{env_role}_REASONING_EFFORT",
            default_effort,
        ),
    )


VOICE_PROFILE = _profile("voice", "medium")
CREATIVE_PROFILE = _profile("creative", "low")
UTILITY_PROFILE = _profile("utility", "low")
ORCHESTRATOR_PROFILE = _profile("orchestrator", "medium")
JUDGE_PROFILE = _profile("judge", "medium")

_PROFILE_BY_AGENT = {
    "heartbreaker_voice": VOICE_PROFILE,
    "npc_greeter": VOICE_PROFILE,
    "event_narrator": CREATIVE_PROFILE,
    "background_dialogue": CREATIVE_PROFILE,
    "contextual_options": UTILITY_PROFILE,
    "conversation_curator": UTILITY_PROFILE,
    "resort_orchestrator": ORCHESTRATOR_PROFILE,
    "trait_generator": UTILITY_PROFILE,
}


def profile_for_agent(agent_name: str) -> AgentModelProfile:
    """Return the shipped profile for a named game agent."""
    return _PROFILE_BY_AGENT.get(
        agent_name,
        AgentModelProfile("default", GAME_AGENT_MODEL, GAME_AGENT_REASONING_EFFORT),
    )


# Bound per-request latency so one slow/hung model call can't freeze a whole
# turn. The OpenAI SDK defaults to a 600s timeout and two automatic retries, so
# a single transient stall mid-ceremony would leave the player waiting for
# minutes before the failure surfaced. With an explicit timeout the call fails
# within a bounded period. Retries are owned by the agent loops (not the
# SDK) so worst-case latency stays bounded at attempts x timeout rather than
# compounding. Both knobs are env-overridable for eval/perf runs.
GAME_AGENT_REQUEST_TIMEOUT = float(os.environ.get("LLM_GAME_REQUEST_TIMEOUT", "60"))
GAME_AGENT_MAX_RETRIES = int(os.environ.get("LLM_GAME_MAX_RETRIES", "0"))


def build_game_client() -> OpenAI:
    """Return the shared, latency-bounded OpenAI client for live game agents.

    Every live agent calls this instead of constructing a bare ``OpenAI()`` so
    the timeout/retry policy lives in one place (see ``GAME_AGENT_REQUEST_TIMEOUT``).
    """
    return OpenAI(timeout=GAME_AGENT_REQUEST_TIMEOUT, max_retries=GAME_AGENT_MAX_RETRIES)


class ReasoningSummary(BaseModel):
    """Model-provided reasoning summary text stored in review traces."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    texts: list[str] = Field(default_factory=list)


class AgentUsage(BaseModel):
    """Responses API token accounting captured without provider internals."""

    model_config = ConfigDict(extra="forbid")

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cached_input_tokens: int | None = None
    cache_write_tokens: int | None = None
    reasoning_tokens: int | None = None


class AgentTrace(BaseModel):
    """One live agent call captured during a turn."""

    model_config = ConfigDict(extra="forbid")

    agent_name: str
    model: str
    reasoning_effort: str
    attempt: int
    prompt_path: str
    prompt_sha256: str | None = None
    input: Any = None
    latency_ms: int | None = None
    usage: AgentUsage | None = None
    response_id: str | None = None
    response_status: str | None = None
    response_details: str | None = None
    output_type: str | None = None
    output: Any = None
    generation_error: str | None = None
    validation_error: str | None = None
    reasoning_summaries: list[ReasoningSummary] = Field(default_factory=list)


class AgentError(Exception):
    """A live agent exhausted its retry or validation contract."""


class AgentGenerationError(AgentError):
    """The model call failed or returned nothing parseable after all retries."""


class AgentValidationError(AgentError):
    """Model output violated the agent's structural contract after all retries."""


_active_traces: ContextVar[list[AgentTrace] | None] = ContextVar(
    "active_agent_traces", default=None
)
_failed_turn_traces: ContextVar[tuple[AgentTrace, ...]] = ContextVar(
    "failed_turn_traces", default=()
)
_active_attempt: ContextVar[int] = ContextVar("active_agent_attempt", default=1)


def reasoning_request_kwargs(effort: str | None = None) -> dict[str, Any]:
    """Return Responses API kwargs shared by all live game agents.

    ``effort`` lets a single agent (e.g. trait_generator) opt into a lower
    reasoning effort than the project default — useful for creative-structured
    work that doesn't need deep chain-of-thought.
    """
    return {
        "reasoning": {
            "effort": effort or GAME_AGENT_REASONING_EFFORT,
            "summary": GAME_AGENT_REASONING_SUMMARY,
        },
        "include": GAME_AGENT_RESPONSE_INCLUDE,
    }


def start_agent_call() -> float:
    """Return a monotonic timestamp for trace latency accounting."""
    return perf_counter()


def begin_agent_trace_capture() -> Token[list[AgentTrace] | None]:
    """Start collecting live agent traces for the current turn."""
    return _active_traces.set([])


def end_agent_trace_capture(token: Token[list[AgentTrace] | None]) -> list[AgentTrace]:
    """Stop collecting traces and return the captured entries."""
    traces = list(_active_traces.get() or [])
    _active_traces.reset(token)
    return traces


def fail_agent_trace_capture(token: Token[list[AgentTrace] | None]) -> None:
    """Close a failed turn capture while retaining traces for its caller."""
    traces = list(_active_traces.get() or [])
    _active_traces.reset(token)
    _failed_turn_traces.set(tuple(traces))


def recover_agent_traces_after_error() -> list[AgentTrace]:
    """Recover traces from a turn that failed before returning a TurnResult."""
    traces = list(_failed_turn_traces.get())
    _failed_turn_traces.set(())
    return traces


def begin_agent_attempt(attempt: int) -> Token[int]:
    """Mark the current retry attempt for the next recorded agent call."""
    return _active_attempt.set(attempt)


def end_agent_attempt(token: Token[int]) -> None:
    """Restore the previous retry-attempt marker."""
    _active_attempt.reset(token)


def record_agent_trace(
    *,
    agent_name: str,
    model: str,
    prompt_path: str,
    response: object,
    output: object,
    reasoning_effort: str = GAME_AGENT_REASONING_EFFORT,
    prompt_text: str | None = None,
    input_payload: object = None,
    started_at: float | None = None,
) -> None:
    """Append one trace entry when turn-level capture is active."""
    traces = _active_traces.get()
    if traces is None:
        return
    trace_output = output if output is not None else _response_output_text(response)
    traces.append(
        AgentTrace(
            agent_name=agent_name,
            model=model,
            reasoning_effort=reasoning_effort,
            attempt=_active_attempt.get(),
            prompt_path=prompt_path,
            prompt_sha256=_prompt_hash(prompt_text),
            input=_dump_output(input_payload),
            latency_ms=(
                round((perf_counter() - started_at) * 1000) if started_at is not None else None
            ),
            usage=_response_usage(response),
            response_id=_response_id(response),
            response_status=_response_status(response),
            response_details=_response_details(response),
            output_type=type(output).__name__
            if output is not None
            else _fallback_output_type(trace_output),
            output=_dump_output(trace_output),
            reasoning_summaries=extract_reasoning_summaries(response),
        )
    )


def mark_agent_trace_validation_error(
    agent_name: str,
    attempt: int,
    error: Exception,
    *,
    prompt_path: str | None = None,
) -> None:
    """Attach a validation failure to the matching captured attempt.

    If no matching trace exists yet (the LLM call itself raised before
    ``record_agent_trace`` ran), append a synthetic trace so the failure
    survives in the review packet.
    """
    traces = _active_traces.get()
    if traces is None:
        return
    profile = profile_for_agent(agent_name)
    for trace in reversed(traces):
        if trace.agent_name == agent_name and trace.attempt == attempt:
            trace.validation_error = str(error)
            return
    traces.append(
        AgentTrace(
            agent_name=agent_name,
            model=profile.model,
            reasoning_effort=profile.reasoning_effort,
            attempt=attempt,
            prompt_path=prompt_path or "",
            validation_error=str(error),
        )
    )


def mark_agent_trace_generation_error(
    agent_name: str,
    attempt: int,
    error: Exception,
    *,
    prompt_path: str | None = None,
) -> None:
    """Attach a provider/generation failure without calling it validation.

    Timeouts, connection failures, and incomplete responses are operational
    generation failures. They remain visible in review packets, but they do not
    fail the separate ``no_agent_validation_retries`` contract when a later
    attempt succeeds with structurally valid output.
    """
    traces = _active_traces.get()
    if traces is None:
        return
    profile = profile_for_agent(agent_name)
    for trace in reversed(traces):
        if trace.agent_name == agent_name and trace.attempt == attempt:
            trace.generation_error = str(error)
            return
    traces.append(
        AgentTrace(
            agent_name=agent_name,
            model=profile.model,
            reasoning_effort=profile.reasoning_effort,
            attempt=attempt,
            prompt_path=prompt_path or "",
            generation_error=str(error),
        )
    )


def extract_reasoning_summaries(response: object) -> list[ReasoningSummary]:
    """Extract Responses API reasoning summary items."""
    output = _get(response, "output")
    if not isinstance(output, list):
        return []
    summaries: list[ReasoningSummary] = []
    for index, item in enumerate(output):
        if _get(item, "type") != "reasoning":
            continue
        texts = _summary_texts(_get(item, "summary"))
        if not texts:
            continue
        item_id = _get(item, "id") or _get(item, "item_id") or f"reasoning-{index}"
        summaries.append(ReasoningSummary(item_id=str(item_id), texts=texts))
    return summaries


def _summary_texts(raw_summary: object) -> list[str]:
    if isinstance(raw_summary, str):
        return [raw_summary] if raw_summary.strip() else []
    if not isinstance(raw_summary, list):
        return []
    texts: list[str] = []
    for item in raw_summary:
        text = _get(item, "text")
        if isinstance(text, str) and text.strip():
            texts.append(text)
    return texts


def _dump_output(output: object) -> object:
    if output is None:
        return None
    model_dump = getattr(output, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="json")
    if isinstance(output, dict):
        return {str(key): _dump_output(value) for key, value in output.items()}
    if isinstance(output, list):
        return [_dump_output(item) for item in output]
    if isinstance(output, (str, int, float, bool)):
        return output
    return str(output)


def _response_id(response: object) -> str | None:
    response_id = _get(response, "id")
    return str(response_id) if response_id is not None else None


def _response_status(response: object) -> str | None:
    status = _get(response, "status")
    return str(status) if status is not None else None


def _response_details(response: object) -> str | None:
    details = _get(response, "incomplete_details") or _get(response, "error")
    if details is None:
        return None
    output = _dump_output(details)
    return output if isinstance(output, str) else str(output)


def _response_output_text(response: object) -> object:
    output_text = _get(response, "output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    output = _get(response, "output")
    if isinstance(output, list):
        return [_public_output_item(item) for item in output]
    return output if output is not None else None


def _public_output_item(item: object) -> dict[str, object]:
    summary = _summary_texts(_get(item, "summary"))
    content = _get(item, "content")
    texts: list[str] = []
    if isinstance(content, list):
        for part in content:
            text = _get(part, "text")
            if isinstance(text, str) and text.strip():
                texts.append(text)
    return {
        "type": str(_get(item, "type") or "item"),
        "status": str(_get(item, "status") or ""),
        "summary": summary,
        "text": texts,
    }


def _fallback_output_type(output: object) -> str | None:
    if output is None:
        return None
    if isinstance(output, str):
        return "raw_response_text"
    return "raw_response_output"


def _prompt_hash(prompt_text: str | None) -> str | None:
    if prompt_text is None:
        return None
    return sha256(prompt_text.encode("utf-8")).hexdigest()


def _response_usage(response: object) -> AgentUsage | None:
    usage = _get(response, "usage")
    if usage is None:
        return None
    input_details = _get(usage, "input_tokens_details")
    output_details = _get(usage, "output_tokens_details")
    return AgentUsage(
        input_tokens=_int_value(_get(usage, "input_tokens")),
        output_tokens=_int_value(_get(usage, "output_tokens")),
        total_tokens=_int_value(_get(usage, "total_tokens")),
        cached_input_tokens=_int_value(_get(input_details, "cached_tokens")),
        cache_write_tokens=_int_value(_get(input_details, "cache_write_tokens")),
        reasoning_tokens=_int_value(_get(output_details, "reasoning_tokens")),
    )


def _int_value(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _get(value: object, key: str) -> object:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)
