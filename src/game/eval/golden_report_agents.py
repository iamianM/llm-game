"""Agent/tool sections for the golden eval HTML report."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_base import escape


def expected_agent_tools(action: dict[str, Any], expected: list[str] | None = None) -> str:
    """Render the expected agent tools for a turn's action.

    The runner is the source of truth — it knows whether ``live_villa_life``
    is on. The report only renders what it is handed.
    """
    tools = expected if expected else ["Engine-only turn"]
    items = "".join(f"<span class='pill'>{escape(tool)}</span>" for tool in tools)
    return f"<div class='pill-row'>{items}</div>"


def actual_agent_tool_responses(record: dict[str, Any]) -> str:
    """Render actual live agent calls, schemas, responses, and reasoning summaries."""
    traces = record.get("agent_traces")
    if not isinstance(traces, list) or not traces:
        return ""
    cards = "".join(_trace_card(trace) for trace in traces if isinstance(trace, dict))
    return f"<section><h3>Actual Agent Tools / Responses</h3><div class='trace-grid'>{cards}</div></section>"


def _trace_card(trace: dict[str, Any]) -> str:
    error = trace.get("validation_error")
    details = trace.get("response_details")
    return (
        "<article class='trace-card'>"
        f"<b>{escape(trace.get('agent_name', 'agent'))}</b>"
        f"<p class='muted'>Tool/schema: {escape(trace.get('output_type') or 'no parsed output')}</p>"
        f"<p class='muted'>{escape(trace.get('model', 'unknown'))} / "
        f"{escape(trace.get('reasoning_effort', 'unknown'))} / "
        f"{escape(trace.get('response_status', 'no status'))} / "
        f"attempt {escape(trace.get('attempt', '?'))}</p>"
        f"{_metadata_line('Response details', details)}"
        f"{_inline_error(error)}"
        f"{_trace_response(trace.get('output'))}"
        f"{_reasoning_summary(trace.get('reasoning_summaries'))}"
        "</article>"
    )


def _trace_response(output: object) -> str:
    return f"<div class='response-block'><b>Actual response</b>{_render_output(output)}</div>"


def _render_output(output: object) -> str:
    if output is None:
        return "<p class='muted'>No parsed or text response captured.</p>"
    if isinstance(output, str):
        return f"<p>{escape(output)}</p>"
    if isinstance(output, dict):
        specialized = _specialized_output(output)
        if specialized:
            return specialized
        rows = "".join(
            f"<li><b>{escape(key)}</b>: {escape(_plain(value))}</li>"
            for key, value in output.items()
        )
        return f"<ul class='compact'>{rows}</ul>"
    if isinstance(output, list):
        items = "".join(f"<li>{escape(_plain(item))}</li>" for item in output)
        return f"<ul class='compact'>{items}</ul>"
    return f"<p>{escape(str(output))}</p>"


def _specialized_output(output: dict[str, Any]) -> str:
    if {"player_dialogue", "npc_dialogue"} <= set(output):
        return (
            "<div class='dialogue'>"
            f"<p><b>Player</b><span>{escape(output.get('player_dialogue', ''))}</span></p>"
            f"<p><b>NPC</b><span>{escape(output.get('npc_dialogue', ''))}</span></p>"
            f"<p class='muted'>Tone: {escape(output.get('npc_tone', 'unknown'))}; "
            f"mood after: {escape(output.get('npc_mood_after', 'unknown'))}</p>"
            "</div>"
        )
    if "options" in output:
        return _options_table(output)
    if "memories" in output:
        return _memory_list(output)
    if "prose" in output:
        return f"<blockquote>{escape(output.get('prose', ''))}</blockquote>"
    if {"speaker_a_line", "speaker_b_line"} <= set(output):
        return (
            "<div class='dialogue'>"
            f"<p><b>A</b><span>{escape(output.get('speaker_a_line', ''))}</span></p>"
            f"<p><b>B</b><span>{escape(output.get('speaker_b_line', ''))}</span></p>"
            f"<p class='muted'>Tone: {escape(output.get('tone', 'unknown'))}</p>"
            "</div>"
        )
    return ""


def _options_table(output: dict[str, Any]) -> str:
    options = output.get("options")
    if not isinstance(options, list):
        return ""
    rows = "".join(
        "<tr>"
        f"<td>{escape(option.get('label', ''))}</td>"
        f"<td>{escape(option.get('category', ''))}</td>"
        f"<td>{escape(option.get('intent_kind', ''))}</td>"
        f"<td>{escape(option.get('risk', ''))}</td>"
        "</tr>"
        for option in options
        if isinstance(option, dict)
    )
    return (
        "<table><thead><tr><th>Label</th><th>Category</th><th>Intent</th><th>Risk</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _memory_list(output: dict[str, Any]) -> str:
    memories = output.get("memories")
    if not isinstance(memories, list):
        return ""
    items = []
    summary = output.get("summary")
    if summary:
        items.append(f"<li><b>Summary</b>: {escape(summary)}</li>")
    for memory in memories:
        if isinstance(memory, dict):
            holder = memory.get("holder_id", "holder")
            subject = memory.get("subject_id", "subject")
            items.append(f"<li><b>{escape(holder)} -> {escape(subject)}</b>: {escape(memory.get('content', ''))}</li>")
    return f"<ul class='compact'>{''.join(items)}</ul>"


def _reasoning_summary(raw: object) -> str:
    if not isinstance(raw, list) or not raw:
        return "<p class='muted'>No reasoning summary item returned by the API for this call.</p>"
    chunks = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        texts = item.get("texts")
        if isinstance(texts, list):
            for text in texts:
                if isinstance(text, str) and text.strip():
                    chunks.append(f"<p>{escape(text)}</p>")
    return "".join(chunks) or "<p class='muted'>No reasoning summary item returned by the API for this call.</p>"


def _metadata_line(label: str, value: object) -> str:
    if value is None or value == "":
        return ""
    return f"<p class='muted'>{escape(label)}: {escape(_plain(value))}</p>"


def _inline_error(value: object) -> str:
    return f"<p class='trace-error'>{escape(value)}</p>" if isinstance(value, str) and value else ""


def _plain(value: object) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{key}: {_plain(item)}" for key, item in value.items())
    if isinstance(value, list):
        return "; ".join(_plain(item) for item in value)
    return str(value)
