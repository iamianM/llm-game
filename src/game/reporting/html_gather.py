"""Gather-event HTML blocks."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_base import escape


def pending_gather_block(record: dict[str, Any]) -> str:
    """Render a pending mandatory gather."""
    gather = record.get("pending_gather")
    if not isinstance(gather, dict):
        return ""
    event = escape(gather.get("event_id", "event"))
    location = escape(gather.get("gather_location", "firepit"))
    return (
        "<div class='card interruption'><p><b>Gather pending</b></p>"
        f"<p>{event} at {location}.</p></div>"
    )
