"""HTML blocks for NPC arrival rolls."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_base import escape


def arrival_roll_block(record: dict[str, Any]) -> str:
    rolls = record.get("arrival_rolls")
    if not isinstance(rolls, list) or not rolls:
        return ""
    items = []
    for item in rolls:
        if not isinstance(item, dict):
            continue
        items.append(
            "<li>"
            f"{escape(str(item.get('arriving_npc_id', 'npc')))} arrived while "
            f"{escape(str(item.get('target_id', 'target')))} was in conversation. "
            f"Interruption {escape(str(item.get('interruption_roll', '?')))}/"
            f"{escape(str(item.get('interruption_chance', '?')))} "
            f"{'hit' if item.get('interruption_hit') is True else 'miss'}; "
            f"pull {escape(str(item.get('pull_roll', '?')))}/"
            f"{escape(str(item.get('pull_chance', '?')))} "
            f"{'hit' if item.get('pull_hit') is True else 'miss'}."
            "</li>"
        )
    return (
        "<div class='card arrival-roll'>"
        "<p><b>Arrival rolls</b></p>"
        f"<ul>{''.join(items)}</ul>"
        "</div>"
    )
