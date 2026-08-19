"""Event-specific HTML blocks."""

from __future__ import annotations

from src.game.reporting.html_base import escape


def challenge_block(challenge: object) -> str:
    """Render a scheduled challenge."""
    if not isinstance(challenge, dict):
        return ""
    deltas = challenge.get("deltas")
    return (
        "<div class='card challenge'>"
        f"<p><b>Challenge:</b> {escape(challenge.get('kind', 'unknown'))} "
        f"({escape(challenge.get('stat_tested', 'stat'))})</p>"
        f"<p>Result: {escape(challenge.get('result', 'pending'))}</p>"
        f"<p class='meta'>Deltas: {escape(deltas if isinstance(deltas, dict) else {})}</p>"
        "</div>"
    )


def producer_text_block(text: object) -> str:
    """Render a producer text."""
    if not isinstance(text, dict):
        return ""
    return (
        "<div class='card producer-text'>"
        f"<p><b>I've got a text:</b> {escape(text.get('body', ''))}</p>"
        f"<p class='meta'>{escape(text.get('kind', 'producer_text'))}</p>"
        "</div>"
    )


def group_date_block(group_date: object) -> str:
    """Render a pending group date."""
    if not isinstance(group_date, dict):
        return ""
    participants = group_date.get("participants")
    label = ", ".join(str(participant) for participant in participants) if isinstance(participants, list) else ""
    return (
        "<div class='card group-date'>"
        f"<p><b>Group date:</b> {escape(label)} at {escape(group_date.get('location', 'unknown'))}</p>"
        f"<p class='meta'>day {escape(group_date.get('day', '?'))}</p>"
        "</div>"
    )


def revealed_preferences_block(revealed: object) -> str:
    """Render currently revealed Ideal-Match preferences."""
    if not isinstance(revealed, dict) or not revealed:
        return ""
    rows = []
    for heartbreaker_id, prefs in revealed.items():
        rows.append(f"<li><b>{escape(heartbreaker_id)}</b>: {escape(prefs)}</li>")
    return f"<div class='card'><p><b>Revealed Ideal Match</b></p><ul>{''.join(rows)}</ul></div>"
