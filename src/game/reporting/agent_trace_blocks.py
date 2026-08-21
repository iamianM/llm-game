"""Review-packet blocks for live agent traces."""

from __future__ import annotations

import json
from typing import Any

from src.game.reporting.html_base import escape


def agent_trace_card(record: dict[str, Any]) -> str:
    """Render agent traces for the older card-style report."""
    body = _agent_trace_body(record)
    if not body:
        return ""
    return f"<div class='card'><p><b>Model reasoning traces</b></p>{body}</div>"


def agent_trace_detail(record: dict[str, Any]) -> str:
    """Render agent traces as a collapsed slide detail."""
    body = _agent_trace_body(record)
    if not body:
        return ""
    return (
        "<details class='inline-detail agent-trace-detail'>"
        "<summary>Model reasoning traces</summary>"
        f"<div class='inline-body'>{body}</div></details>"
    )


def _agent_trace_body(record: dict[str, Any]) -> str:
    traces = record.get("agent_traces")
    if not isinstance(traces, list) or not traces:
        return ""
    return "".join(_trace_item(trace) for trace in traces if isinstance(trace, dict))


def _trace_item(trace: dict[str, Any]) -> str:
    agent_name = str(trace.get("agent_name") or "agent")
    model = str(trace.get("model") or "unknown")
    effort = str(trace.get("reasoning_effort") or "unknown")
    status = str(trace.get("response_status") or "")
    attempt = trace.get("attempt")
    output_type = str(trace.get("output_type") or "")
    generation_error = trace.get("generation_error")
    validation_error = trace.get("validation_error")
    generation_error_html = (
        f"<div class='miss'>Generation error: {escape(generation_error)}</div>"
        if isinstance(generation_error, str) and generation_error
        else ""
    )
    validation_error_html = (
        f"<div class='miss'>Validation error: {escape(validation_error)}</div>"
        if isinstance(validation_error, str) and validation_error
        else ""
    )
    return (
        "<div class='agent-trace-item'>"
        f"<div><b>{escape(agent_name)}</b> "
        f"<span class='muted small'>{escape(model)} / {escape(effort)}"
        f"{' / ' + escape(status) if status else ''}"
        f"{' / attempt ' + escape(attempt) if attempt is not None else ''}"
        f"{' / ' + escape(output_type) if output_type else ''}</span></div>"
        f"{generation_error_html}{validation_error_html}"
        f"{_reasoning_summaries(trace)}"
        f"{_trace_output(trace)}"
        "</div>"
    )


def _reasoning_summaries(trace: dict[str, Any]) -> str:
    raw_items = trace.get("reasoning_summaries")
    if not isinstance(raw_items, list) or not raw_items:
        return "<p class='muted small'>No reasoning summary returned.</p>"
    blocks: list[str] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("item_id") or "reasoning")
        texts = item.get("texts")
        if not isinstance(texts, list):
            continue
        for text in texts:
            if isinstance(text, str) and text.strip():
                blocks.append(
                    f"<div class='muted small'>{escape(item_id)}</div>"
                    f"<pre>{escape(text)}</pre>"
                )
    return "".join(blocks) or "<p class='muted small'>No reasoning summary returned.</p>"


def _trace_output(trace: dict[str, Any]) -> str:
    output = trace.get("output")
    if output is None:
        return ""
    try:
        rendered = json.dumps(output, indent=2, sort_keys=True)
    except TypeError:
        rendered = str(output)
    return (
        "<details><summary>Parsed output</summary>"
        f"<pre>{escape(rendered)}</pre></details>"
    )
