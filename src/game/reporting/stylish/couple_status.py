"""Couple status sidebar for stylish reports."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_base import escape
from src.game.reporting.stylish.avatars import avatar_svg


def couple_status_panel(records: list[dict[str, Any]]) -> str:
    """Render sticky couple status from audience snapshots and trace fields."""
    latest = _latest_audience(records)
    rows = []
    if latest:
        for entry in latest.get("entries", []):
            if not isinstance(entry, dict):
                continue
            couple = entry.get("couple")
            if not isinstance(couple, list):
                continue
            strength = _latest_player_strength(records) if entry.get("is_player_couple") else None
            rows.append(_couple_row([str(item) for item in couple], entry, strength))
    elif _latest_player_strength(records) is not None:
        rows.append(_couple_row(["player", "partner"], {"is_player_couple": True}, _latest_player_strength(records)))
    content = "".join(rows) if rows else "<p class='meta'>No couples yet.</p>"
    return f"<aside class='panel right'><h2>Couples</h2>{content}</aside>"


def _couple_row(partners: list[str], entry: dict[str, Any], strength: int | None) -> str:
    names = " & ".join(partners)
    avatars = "".join(avatar_svg(partner, partner.title(), size=28) for partner in partners)
    player_class = " player" if entry.get("is_player_couple") else ""
    score = entry.get("score", "n/a")
    bar = ""
    if isinstance(strength, int):
        bar = f"<div class='bar-bg'><span class='bar' style='width:{max(0, min(100, strength))}%'></span></div>"
    return (
        f"<div class='couple{player_class}'>{avatars}<b>{escape(names)}</b>"
        f"<p class='meta'>Audience {escape(score)}{'; CS ' + str(strength) if strength is not None else ''}</p>{bar}</div>"
    )


def _latest_audience(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    for record in reversed(records):
        snapshot = record.get("audience_snapshot")
        if isinstance(snapshot, dict):
            return snapshot
    return None


def _latest_player_strength(records: list[dict[str, Any]]) -> int | None:
    for record in reversed(records):
        strength = record.get("couple_strength")
        if isinstance(strength, int):
            return strength
    return None
