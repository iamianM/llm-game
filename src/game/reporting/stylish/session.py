"""Stylish session report composition."""

from __future__ import annotations

from typing import Any

from src.game.reporting.slides.session import slide_session_page


def stylish_session_page(
    title: str,
    records: list[dict[str, Any]],
    preface: str = "",
    reviewer_notes: list[dict[str, object]] | None = None,
) -> str:
    """Render a self-contained editorial session report."""
    return slide_session_page(title, records, preface=preface, reviewer_notes=reviewer_notes)
