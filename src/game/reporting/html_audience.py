"""Audience-specific HTML blocks."""

from __future__ import annotations

from src.game.reporting.html_base import escape


def audience_block(snapshot: object) -> str:
    """Render an audience ranking snapshot."""
    if not isinstance(snapshot, dict):
        return ""
    entries = snapshot.get("entries")
    if not isinstance(entries, list) or not entries:
        return ""
    rows = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        couple = entry.get("couple")
        couple_label = " & ".join(str(item) for item in couple) if isinstance(couple, list) else "unknown"
        marker = " (you)" if entry.get("is_player_couple") else ""
        rows.append(
            f"<li>#{escape(entry.get('rank', '?'))}: {escape(couple_label)}"
            f"{marker} - {escape(entry.get('score', '?'))}</li>"
        )
    return (
        "<div class='card'>"
        f"<p><b>Audience ranking - day {escape(snapshot.get('day', '?'))}</b></p>"
        f"<ol>{''.join(rows)}</ol>"
        "</div>"
    )
