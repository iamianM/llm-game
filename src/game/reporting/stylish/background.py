"""Background-life blocks for stylish reports."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_base import escape


def background_dialogue_block(record: dict[str, Any]) -> str:
    """Render full background dialogue commits for one turn."""
    commits = record.get("agent_commits")
    if not isinstance(commits, dict):
        return ""
    dialogues = commits.get("background_dialogues")
    if not isinstance(dialogues, list) or not dialogues:
        return ""
    rows = []
    for item in dialogues:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<div class='bg-exchange'>"
            f"<p class='meta'>{escape(item.get('tone', 'unknown'))}: "
            f"{escape(item.get('speaker_a_id', 'npc'))} / {escape(item.get('speaker_b_id', 'npc'))}</p>"
            f"<p><i>{escape(item.get('speaker_a_line', ''))}</i></p>"
            f"<p><i>{escape(item.get('speaker_b_line', ''))}</i></p>"
            "</div>"
        )
    return "<div class='card background'><p><b>Background dialogue</b></p>" + "".join(rows) + "</div>"


def daily_recap_block(day: int, records: list[dict[str, Any]]) -> str:
    """Render the latest recap for the previous day at the top of a day section."""
    recap = _recap_for_day(day - 1, records)
    if recap is None:
        return ""
    items = recap.get("items")
    if not isinstance(items, list):
        return ""
    resort_label = escape(recap.get("resort_label", "Sunset Bay"))
    if not items:
        body = f"<p>No major {resort_label} memories surfaced.</p>"
    else:
        body = "".join(
            _recap_section(items, section, label)
            for section, label in (
                ("your_day", "Your day"),
                ("while_busy", "While you were busy"),
            )
        )
    return f"<div class='card background'><p><b>Daily Recap</b></p>{body}</div>"


def _recap_for_day(day: int, records: list[dict[str, Any]]) -> dict[str, object] | None:
    for record in records:
        recaps = record.get("daily_recaps")
        if not isinstance(recaps, list):
            continue
        for recap in recaps:
            if isinstance(recap, dict) and recap.get("day") == day:
                return recap
    return None


def _recap_item(item: dict[str, object]) -> str:
    return (
        "<li>"
        f"<b>{escape(item.get('speaker_label', 'Someone'))}:</b> "
        f"{escape(item.get('content', ''))}"
        "</li>"
    )


def _recap_section(items: list[object], section: str, label: str) -> str:
    matching = [
        item
        for item in items
        if isinstance(item, dict) and item.get("section") == section
    ]
    if not matching:
        return ""
    rows = "".join(_recap_item(item) for item in matching)
    return f"<p><b>{escape(label)}</b></p><ul>{rows}</ul>"
