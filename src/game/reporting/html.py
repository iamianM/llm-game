"""Self-contained HTML rendering for review packets."""

from __future__ import annotations

import html
from collections.abc import Iterable
from typing import Any

CSS = """
body{font-family:Inter,Segoe UI,Arial,sans-serif;margin:0;background:#f7f4ef;color:#27231f}
main{max-width:1100px;margin:0 auto;padding:32px}
a{color:#7a2d12} code{font-size:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
.card,.turn{background:#fff;border:1px solid #d8d0c2;border-radius:8px;padding:16px;margin:12px 0}
.turn summary{cursor:pointer;font-size:22px;font-weight:700}
.meta{color:#655d52;font-size:14px}.success{color:#17633a}.miss{color:#9b2d20}
.pill{display:inline-block;border:1px solid #d8d0c2;border-radius:999px;padding:4px 10px;margin:2px;background:#fff}
.math{border-left:4px solid #17633a}.pull-attempt{border-left:4px solid #d8793f}.interruption{border-left:4px solid #6b3fa0}.memory{border-left:4px solid #7a2d12}
table{border-collapse:collapse;width:100%;background:#fff}th,td{border:1px solid #d8d0c2;padding:8px;text-align:left}
.bar{height:14px;background:#d8793f;display:inline-block;vertical-align:middle}
"""


def page(title: str, body: str) -> str:
    """Wrap body HTML in a self-contained document."""
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{escape(title)}</title><style>{CSS}</style></head>"
        f"<body><main><h1>{escape(title)}</h1>{body}</main></body></html>"
    )


def session_page(title: str, records: list[dict[str, Any]], preface: str = "") -> str:
    """Render one session trace as turn cards.

    ``preface`` is optional self-contained HTML inserted above the first turn —
    useful for previews that pre-warm state and need to disclose that to readers.
    """
    cards = []
    if preface:
        cards.append(f"<section class='card'>{preface}</section>")
    collapsible = len(records) >= 30
    for record in records:
        result = record["mechanical_result"]
        action = result["action"]
        outcome_class = "success" if result["success"] else "miss"
        visible = record.get("visible_state", "")
        header = (
            f"Turn {record['turn']} - Day {record['day']} - "
            f"{escape(record['phase'])} - {escape(record['location'])}"
        )
        open_attr = "" if collapsible else " open"
        cards.append(
            f"<details class='turn' id='turn-{escape(record['turn'])}'{open_attr}>"
            f"<summary>{header}</summary>"
            f"<p class='meta'>{escape(visible)}</p>"
            f"{_villa_snapshot_block(record.get('villa_snapshot'))}"
            f"<p><b>You chose:</b> {escape(action['kind'])} "
            f"{escape(str(action.get('target_id') or ''))} "
            f"{escape(str(action.get('intent_id') or ''))}</p>"
            f"{_math_block(result)}"
            f"{_pull_attempt_block(result.get('pull_attempt'))}"
            f"{_exchange_block(record.get('exchange'))}"
            f"{_event_block(record.get('event_narration'))}"
            f"{_follow_up_block(record.get('follow_up_menu'))}"
            f"{_interruption_block(record)}"
            f"{_agent_commit_block(record.get('agent_commits'))}"
            f"{_memory_block(record.get('agent_commits'))}"
            f"<p><b>Roll:</b> {escape(str(result.get('roll')))} vs "
            f"{escape(str(result.get('success_chance')))} "
            f"<span class='{outcome_class}'>{'Success' if result['success'] else 'Miss'}</span></p>"
            f"<p><b>Deltas:</b> {escape(_delta_text(result))}</p>"
            f"<p><b>Hash:</b> <code>{escape(record['output_hash'])}</code></p>"
            "</details>"
        )
    return page(title, "".join(cards))


def index_page(links: Iterable[tuple[str, str]]) -> str:
    """Render packet index links."""
    items = "".join(
        f"<div class='card'><a href='{escape(href)}'>{escape(label)}</a></div>"
        for label, href in links
    )
    return page("Review Packet", f"<div class='grid'>{items}</div>")


def table_page(title: str, headers: list[str], rows: list[list[str]]) -> str:
    """Render a simple table page."""
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return page(title, f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")


def escape(value: object) -> str:
    """HTML-escape any value."""
    return html.escape(str(value), quote=True)


def _exchange_block(exchange: object) -> str:
    if not isinstance(exchange, dict):
        return ""
    return (
        "<div class='card'>"
        f"<p><b>You:</b> {escape(exchange.get('player_dialogue', ''))}</p>"
        f"<p><b>Islander:</b> {escape(exchange.get('npc_dialogue', ''))}</p>"
        f"<p class='meta'>Tone: {escape(exchange.get('npc_tone', ''))}; "
        f"mood after: {escape(exchange.get('npc_mood_after', ''))}</p>"
        "</div>"
    )


def _event_block(event_narration: object) -> str:
    if not isinstance(event_narration, dict):
        return ""
    return (
        "<div class='card'>"
        f"<p><b>Event:</b> {escape(event_narration.get('prose', ''))}</p>"
        "</div>"
    )


def _follow_up_block(menu: object) -> str:
    if not isinstance(menu, dict):
        return ""
    options = menu.get("options")
    grouped: dict[str, list[str]] = {}
    if isinstance(options, list):
        for option in options:
            if not isinstance(option, dict):
                continue
            category = str(option.get("category", "other"))
            grouped.setdefault(category, []).append(
                f"<li>{escape(option.get('label', ''))} "
                f"<span class='meta'>({escape(option.get('intent_kind', ''))}, "
                f"{escape(option.get('risk', ''))})</span></li>"
            )
    option_groups = "".join(
        f"<h3>{escape(category.title())}</h3><ol>{''.join(items)}</ol>"
        for category, items in grouped.items()
    )
    exit_line = menu.get("npc_exit_line")
    exit_text = f"<p><b>Exit:</b> {escape(exit_line)}</p>" if exit_line else ""
    return (
        "<div class='card'>"
        "<p><b>Follow-up menu</b></p>"
        f"{option_groups}"
        f"{exit_text}"
        "</div>"
    )


def _agent_commit_block(agent_commits: object) -> str:
    if not isinstance(agent_commits, dict):
        return ""
    update = agent_commits.get("villa_update")
    if not isinstance(update, dict):
        return ""
    movements = update.get("npc_movements")
    starts = update.get("conversation_starts")
    continues = update.get("conversation_continues")
    ends = update.get("conversation_ends")
    interruptions = update.get("npc_interruptions")
    background = agent_commits.get("background_dialogues")
    batches = agent_commits.get("curator_batches")
    rows = [
        f"<li>Movements: {len(movements) if isinstance(movements, list) else 0}</li>",
        f"<li>Starts: {len(starts) if isinstance(starts, list) else 0}</li>",
        f"<li>Continues: {len(continues) if isinstance(continues, list) else 0}</li>",
        f"<li>Ends: {len(ends) if isinstance(ends, list) else 0}</li>",
        f"<li>Interruptions: {len(interruptions) if isinstance(interruptions, list) else 0}</li>",
        f"<li>Background dialogue commits: {len(background) if isinstance(background, list) else 0}</li>",
        f"<li>Curator batches: {len(batches) if isinstance(batches, list) else 0}</li>",
    ]
    details = _agent_commit_details(update, background)
    return (
        "<div class='card'>"
        "<p><b>Villa agent commits</b></p>"
        f"<ul>{''.join(rows)}</ul>"
        f"{details}"
        "</div>"
    )


def _agent_commit_details(update: dict[str, object], background: object) -> str:
    lines: list[str] = []
    movements = update.get("npc_movements")
    if isinstance(movements, list):
        for item in movements:
            if isinstance(item, dict):
                lines.append(
                    f"{escape(str(item.get('npc_id', 'npc')))} moved to "
                    f"{escape(str(item.get('target_location', 'unknown')))} "
                    f"({escape(str(item.get('reason', '')))})."
                )
    starts = update.get("conversation_starts")
    if isinstance(starts, list):
        for item in starts:
            if isinstance(item, dict):
                participants = item.get("participants")
                label = " & ".join(str(value) for value in participants) if isinstance(participants, list) else "NPCs"
                lines.append(
                    f"{escape(label)} started at {escape(str(item.get('location', 'unknown')))}: "
                    f"\"{escape(str(item.get('topic', '')))}\"."
                )
    continues = update.get("conversation_continues")
    if isinstance(continues, list):
        for item in continues:
            if isinstance(item, dict):
                nudge = str(item.get("nudge", ""))
                suffix = f": \"{escape(nudge)}\"" if nudge else ""
                lines.append(f"{escape(str(item.get('conversation_id', 'conversation')))} continued{suffix}.")
    ends = update.get("conversation_ends")
    if isinstance(ends, list):
        for item in ends:
            if isinstance(item, dict):
                lines.append(
                    f"{escape(str(item.get('conversation_id', 'conversation')))} ended: "
                    f"{escape(str(item.get('reason', '')))}."
                )
    interruptions = update.get("npc_interruptions")
    if isinstance(interruptions, list):
        for item in interruptions:
            if isinstance(item, dict):
                lines.append(
                    f"{escape(str(item.get('interrupter_id', 'npc')))} interrupted: "
                    f"{escape(str(item.get('reason', '')))} / {escape(str(item.get('urgency', '')))}."
                )
    if isinstance(background, list):
        for item in background:
            if isinstance(item, dict):
                lines.append(
                    f"Background ({escape(str(item.get('tone', 'unknown')))}): "
                    f"\"{escape(_short_text(str(item.get('speaker_a_line', ''))))}\""
                )
    if not lines:
        return ""
    return f"<p><b>Details</b></p><ul>{''.join(f'<li>{line}</li>' for line in lines)}</ul>"


def _pull_attempt_block(pull_attempt: object) -> str:
    if not isinstance(pull_attempt, dict):
        return ""
    outcome = "success" if pull_attempt.get("success") else "miss"
    deflection = pull_attempt.get("deflection_line")
    deflection_html = (
        "" if not isinstance(deflection, str) or not deflection else f"<p>{escape(deflection)}</p>"
    )
    return (
        "<div class='card pull-attempt'>"
        "<p><b>Pull attempt</b></p>"
        f"<p>Target: {escape(str(pull_attempt.get('target_id', 'unknown')))}; "
        f"chance {escape(str(pull_attempt.get('chance', '')))}; "
        f"roll {escape(str(pull_attempt.get('roll', '')))}; "
        f"outcome {escape(outcome)}.</p>"
        f"{deflection_html}"
        "</div>"
    )


def _villa_snapshot_block(snapshot: object) -> str:
    if not isinstance(snapshot, dict):
        return ""
    rows = []
    for location, occupants in snapshot.items():
        if not isinstance(occupants, list):
            continue
        rows.append(f"<li>{escape(location)}: {escape(', '.join(str(item) for item in occupants) or '(empty)')}</li>")
    if not rows:
        return ""
    return f"<div class='card'><p><b>Villa snapshot</b></p><ul>{''.join(rows)}</ul></div>"


def _math_block(result: dict[str, Any]) -> str:
    roll = result.get("roll")
    chance = result.get("success_chance")
    if not isinstance(roll, int) or not isinstance(chance, int):
        return ""
    outcome = "success" if result.get("success") else "miss"
    tags = result.get("tags")
    tag_text = ", ".join(str(tag) for tag in tags) if isinstance(tags, list) else "none"
    return (
        "<div class='card math'>"
        "<p><b>Success math</b></p>"
        f"<p>Final chance {chance}%. Rolled {roll}. Outcome: "
        f"<span class='{'success' if outcome == 'success' else 'miss'}'>{escape(outcome)}</span>.</p>"
        f"<p class='meta'>Tags: {escape(tag_text)}</p>"
        "</div>"
    )


def _interruption_block(record: dict[str, Any]) -> str:
    commits = record.get("agent_commits")
    if not isinstance(commits, dict):
        return ""
    update = commits.get("villa_update")
    if not isinstance(update, dict):
        return ""
    interruptions = update.get("npc_interruptions")
    if not isinstance(interruptions, list) or not interruptions:
        return ""
    action = record.get("action")
    response = ""
    if isinstance(action, dict) and action.get("intent_id") in {
        "accept_interruption",
        "defer_interruption",
        "ignore_interruption",
    }:
        response = f"<p><b>Player response:</b> {escape(action.get('intent_id'))}</p>"
    items = "".join(
        f"<li>{escape(item.get('interrupter_id', 'npc'))}: {escape(item.get('reason', ''))}, "
        f"{escape(item.get('urgency', ''))}</li>"
        for item in interruptions
        if isinstance(item, dict)
    )
    return (
        "<div class='card interruption'>"
        "<p><b>NPC interruption</b></p>"
        f"<ul>{items}</ul>{response}"
        "</div>"
    )


def _memory_block(agent_commits: object) -> str:
    if not isinstance(agent_commits, dict):
        return ""
    batches = agent_commits.get("curator_batches")
    if not isinstance(batches, list) or not batches:
        return ""
    rows = []
    for batch in batches:
        if not isinstance(batch, dict):
            continue
        memories = batch.get("memories")
        if not isinstance(memories, list):
            continue
        for memory in memories:
            if not isinstance(memory, dict):
                continue
            tags = memory.get("tags")
            tag_text = ", ".join(str(tag) for tag in tags) if isinstance(tags, list) else ""
            rows.append(
                "<li>"
                f"<b>{escape(memory.get('holder_id', 'holder'))}</b> about "
                f"{escape(memory.get('subject_id', 'subject'))}: "
                f"{escape(memory.get('content', ''))} "
                f"<span class='meta'>weight {escape(memory.get('emotional_weight', ''))}; "
                f"{escape(tag_text)}</span></li>"
            )
    if not rows:
        return ""
    return f"<div class='card memory'><p><b>Memories formed this turn</b></p><ul>{''.join(rows)}</ul></div>"


def _short_text(value: str, *, limit: int = 140) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def _delta_text(result: dict[str, Any]) -> str:
    deltas = ", ".join(
        f"{target}: {delta}"
        for target, delta in result.get("relationship_deltas", {}).items()
    )
    return deltas or "none"
