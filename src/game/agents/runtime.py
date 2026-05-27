"""Shared live-agent model settings and trace capture."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

GAME_AGENT_MODEL = "gpt-5.4-mini"
GAME_AGENT_REASONING_EFFORT = "high"
GAME_AGENT_REASONING_SUMMARY = "detailed"
GAME_AGENT_RESPONSE_INCLUDE = ["reasoning.encrypted_content"]


class ReasoningSummary(BaseModel):
    """Model-provided reasoning summary text stored in review traces."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    texts: list[str] = Field(default_factory=list)


class AgentTrace(BaseModel):
    """One live agent call captured during a turn."""

    model_config = ConfigDict(extra="forbid")

    agent_name: str
    model: str
    reasoning_effort: str
    attempt: int
    prompt_path: str
    response_id: str | None = None
    response_status: str | None = None
    response_details: str | None = None
    output_type: str | None = None
    output: Any = None
    validation_error: str | None = None
    reasoning_summaries: list[ReasoningSummary] = Field(default_factory=list)


_active_traces: ContextVar[list[AgentTrace] | None] = ContextVar("active_agent_traces", default=None)
_active_attempt: ContextVar[int] = ContextVar("active_agent_attempt", default=1)


def reasoning_request_kwargs() -> dict[str, Any]:
    """Return Responses API kwargs shared by all live game agents."""
    return {
        "reasoning": {
            "effort": GAME_AGENT_REASONING_EFFORT,
            "summary": GAME_AGENT_REASONING_SUMMARY,
        },
        "include": GAME_AGENT_RESPONSE_INCLUDE,
    }


def begin_agent_trace_capture() -> Token[list[AgentTrace] | None]:
    """Start collecting live agent traces for the current turn."""
    return _active_traces.set([])


def end_agent_trace_capture(token: Token[list[AgentTrace] | None]) -> list[AgentTrace]:
    """Stop collecting traces and return the captured entries."""
    traces = list(_active_traces.get() or [])
    _active_traces.reset(token)
    return traces


def recover_agent_traces_after_error() -> list[AgentTrace]:
    """Recover traces from a turn that failed before returning a TurnResult."""
    traces = list(_active_traces.get() or [])
    _active_traces.set(None)
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
            reasoning_effort=GAME_AGENT_REASONING_EFFORT,
            attempt=_active_attempt.get(),
            prompt_path=prompt_path,
            response_id=_response_id(response),
            response_status=_response_status(response),
            response_details=_response_details(response),
            output_type=type(output).__name__ if output is not None else _fallback_output_type(trace_output),
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
    for trace in reversed(traces):
        if trace.agent_name == agent_name and trace.attempt == attempt:
            trace.validation_error = str(error)
            return
    traces.append(
        AgentTrace(
            agent_name=agent_name,
            model=GAME_AGENT_MODEL,
            reasoning_effort=GAME_AGENT_REASONING_EFFORT,
            attempt=attempt,
            prompt_path=prompt_path or "",
            validation_error=str(error),
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
    dumped = _dump_output(details)
    return dumped if isinstance(dumped, str) else str(dumped)


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


def _get(value: object, key: str) -> object:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)
