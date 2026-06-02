"""Day navigation and timeline grouping."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.game.reporting.html_base import escape


def day_nav(records: list[dict[str, Any]]) -> str:
    """Render sticky day navigation."""
    days = sorted({int(record.get("day", 0)) for record in records if isinstance(record.get("day"), int)})
    links = []
    for day in days:
        icon = _day_icon(day, records)
        links.append(f"<a href='#day-{day}'>{icon} Day {day}</a>")
    return f"<nav class='panel day-nav'><h2>Days</h2>{''.join(links)}</nav>"


def grouped_days(records: list[dict[str, Any]]) -> list[tuple[int, list[dict[str, Any]]]]:
    """Group records by day in display order."""
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        day = record.get("day")
        if isinstance(day, int):
            grouped[day].append(record)
    return sorted(grouped.items())


def day_heading(day: int, records: list[dict[str, Any]]) -> str:
    """Render one day heading with highlight tags."""
    tags = sorted({_highlight(record) for record in records if _highlight(record)})
    label = " | ".join(tags) if tags else "Sunset Bay life"
    return f"<h2 id='day-{day}'>Day {day} <span class='meta'>{escape(label)}</span></h2>"


def _day_icon(day: int, records: list[dict[str, Any]]) -> str:
    day_records = [record for record in records if record.get("day") == day]
    highlights = {_highlight(record) for record in day_records}
    if "Flush of Hearts" in highlights:
        return "★"
    if "Drama" in highlights:
        return "★"
    if "Pairing" in highlights:
        return "◆"
    if "Challenge" in highlights:
        return "▲"
    return "●"


def _highlight(record: dict[str, Any]) -> str:
    if record.get("challenge"):
        return "Challenge"
    for event in record.get("ceremony_events", []) if isinstance(record.get("ceremony_events"), list) else []:
        if isinstance(event, dict) and event.get("kind") in {"pairing", "steal_attempt"}:
            return "Pairing"
        if isinstance(event, dict) and event.get("kind") in {"heart_throb", "elimination"}:
            return "Drama"
        if isinstance(event, dict) and str(event.get("kind", "")).startswith("flush"):
            return "Flush of Hearts"
    return ""
