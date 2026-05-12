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
.meta{color:#655d52;font-size:14px}.success{color:#17633a}.miss{color:#9b2d20}
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
    for record in records:
        result = record["mechanical_result"]
        action = result["action"]
        outcome_class = "success" if result["success"] else "miss"
        visible = record.get("visible_state", "")
        cards.append(
            "<section class='turn'>"
            f"<h2>Turn {record['turn']} - Day {record['day']} - "
            f"{escape(record['phase'])} - {escape(record['location'])}</h2>"
            f"<p class='meta'>{escape(visible)}</p>"
            f"<p><b>You chose:</b> {escape(action['kind'])} "
            f"{escape(str(action.get('target_id') or ''))} "
            f"{escape(str(action.get('intent_id') or ''))}</p>"
            f"{_exchange_block(record.get('exchange'))}"
            f"{_event_block(record.get('event_narration'))}"
            f"<p><b>Roll:</b> {escape(str(result.get('roll')))} vs "
            f"{escape(str(result.get('success_chance')))} "
            f"<span class='{outcome_class}'>{'Success' if result['success'] else 'Miss'}</span></p>"
            f"<p><b>Deltas:</b> {escape(_delta_text(result))}</p>"
            f"<p><b>Hash:</b> <code>{escape(record['output_hash'])}</code></p>"
            "</section>"
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


def _delta_text(result: dict[str, Any]) -> str:
    deltas = ", ".join(
        f"{target}: {delta}"
        for target, delta in result.get("relationship_deltas", {}).items()
    )
    return deltas or "none"
