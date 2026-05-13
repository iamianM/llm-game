"""Deterministic avatar SVG helpers."""

from __future__ import annotations

import hashlib

from src.game.reporting.html_base import escape

PALETTE = ["#a4341a", "#5b7c4f", "#3a5a73", "#8c5a7a", "#b06b2c", "#496b63"]


def avatar_svg(actor_id: str, name: str, *, size: int = 32) -> str:
    """Return a self-contained SVG avatar for an actor."""
    color = PALETTE[int(hashlib.sha256(actor_id.encode()).hexdigest()[:2], 16) % len(PALETTE)]
    initials = _initials(name or actor_id)
    mid = size // 2
    text_y = mid + max(4, size // 8)
    font_size = max(10, size // 3)
    return (
        f"<svg class='avatar' width='{size}' height='{size}' viewBox='0 0 {size} {size}' "
        "role='img' aria-label='avatar'>"
        f"<circle cx='{mid}' cy='{mid}' r='{mid - 1}' fill='{color}'/>"
        f"<text x='{mid}' y='{text_y}' text-anchor='middle' font-size='{font_size}' "
        f"font-family='Inter,sans-serif' fill='white'>{escape(initials)}</text></svg>"
    )


def _initials(name: str) -> str:
    parts = [part for part in name.replace("_", " ").split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return f"{parts[0][0]}{parts[-1][0]}".upper()
