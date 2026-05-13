"""Stylish session report composition."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_base import escape
from src.game.reporting.html_blocks import (
    agent_commit_block,
    autopilot_block,
    casa_amor_block,
    couple_status_block,
    delta_text,
    event_block,
    exchange_block,
    follow_up_block,
    interruption_block,
    memory_block,
    pull_attempt_block,
    time_block,
    villa_snapshot_block,
)
from src.game.reporting.html_events import challenge_block, group_date_block, producer_text_block
from src.game.reporting.html_math import math_block
from src.game.reporting.memory_web import memory_web_svg
from src.game.reporting.stylish.avatars import avatar_svg
from src.game.reporting.stylish.couple_status import couple_status_panel
from src.game.reporting.stylish.css import STYLISH_CSS
from src.game.reporting.stylish.perception_graph import perception_graph_svg
from src.game.reporting.stylish.timeline import day_heading, day_nav, grouped_days


def stylish_session_page(title: str, records: list[dict[str, Any]], preface: str = "") -> str:
    """Render a self-contained editorial session report."""
    body = (
        "<div class='shell'>"
        f"<header class='hero'><h1>{escape(title)}</h1>{preface}<p>{_summary(records)}</p></header>"
        "<div class='layout'>"
        f"<div class='left'>{day_nav(records)}</div>"
        f"<main>{_timeline(records)}<div class='viz'>{perception_graph_svg(records)}{memory_web_svg(records)}</div></main>"
        f"{couple_status_panel(records)}"
        "</div></div>"
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{escape(title)}</title><style>{STYLISH_CSS}</style></head><body>{body}</body></html>"
    )


def _timeline(records: list[dict[str, Any]]) -> str:
    sections = []
    for day, day_records in grouped_days(records):
        cards = "".join(_turn_card(record) for record in day_records)
        sections.append(f"<section>{day_heading(day, day_records)}{cards}</section>")
    return "".join(sections)


def _turn_card(record: dict[str, Any]) -> str:
    result = record["mechanical_result"]
    action = result["action"]
    outcome_class = "success" if result["success"] else "miss"
    target_id = str(action.get("target_id") or "player")
    header = (
        f"Turn {record['turn']} - {escape(record['phase'])} - "
        f"{escape(record['location'])}"
    )
    hideaway_class = " hideaway" if action.get("kind") == "hideaway" else ""
    return (
        f"<details class='turn{hideaway_class}' id='turn-{escape(record['turn'])}' open>"
        f"<summary>{avatar_svg('player', 'Player', size=26)} {avatar_svg(target_id, target_id.title(), size=26)} {header}</summary>"
        f"<p class='meta'>{escape(record.get('visible_state', ''))}</p>"
        f"{villa_snapshot_block(record.get('villa_snapshot'))}{time_block(record)}{casa_amor_block(record)}{couple_status_block(record)}"
        f"{challenge_block(record.get('challenge'))}{producer_text_block(record.get('producer_text'))}{group_date_block(record.get('group_date'))}"
        f"<p><b>You chose:</b> {escape(action['kind'])} {escape(str(action.get('target_id') or ''))} {escape(str(action.get('intent_id') or ''))}</p>"
        f"{autopilot_block(record.get('agent_commits'))}"
        f"<div class='math'><details><summary>Success math</summary>{math_block(result)}</details></div>"
        f"{pull_attempt_block(result.get('pull_attempt'))}<div class='dialogue'>{exchange_block(record.get('exchange'))}</div>"
        f"{event_block(record.get('event_narration'))}{follow_up_block(record.get('follow_up_menu'))}"
        f"{interruption_block(record)}{agent_commit_block(record.get('agent_commits'))}{memory_block(record.get('agent_commits'))}"
        f"<p><b>Roll:</b> {escape(str(result.get('roll')))} vs {escape(str(result.get('success_chance')))} "
        f"<span class='{outcome_class}'>{'Success' if result['success'] else 'Miss'}</span></p>"
        f"<p><b>Deltas:</b> {escape(delta_text(result))}</p>"
        f"<p><b>Hash:</b> <code>{escape(record['output_hash'])}</code></p></details>"
    )


def _summary(records: list[dict[str, Any]]) -> str:
    if not records:
        return "No turns recorded."
    last = records[-1]
    return f"{len(records)} turns recorded through day {escape(last.get('day', '?'))}."
