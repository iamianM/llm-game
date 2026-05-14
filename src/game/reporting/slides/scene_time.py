"""Time and phase labels for slide scene rendering."""

from __future__ import annotations

from typing import Any

PHASE_LABEL = {
    "morning": "Morning",
    "intros": "Intros",
    "challenge": "Challenge",
    "afternoon": "Afternoon",
    "text": "Text",
    "evening": "Evening",
    "night": "Night",
}

PHASE_ANCHOR_MINUTES = {
    "morning": 9 * 60,
    "challenge": 11 * 60,
    "afternoon": 14 * 60,
    "text": 18 * 60,
    "evening": 20 * 60,
    "night": 22 * 60 + 30,
}


def phase_label(phase: str) -> str:
    """Return a human-friendly label for an engine phase string."""
    if not phase:
        return ""
    p = str(phase)
    return PHASE_LABEL.get(p, p.replace("_", " ").title())


def _fmt_clock(total_minutes: int) -> str:
    total_minutes = max(0, total_minutes)
    return f"{(total_minutes // 60) % 24:02d}:{total_minutes % 60:02d}"


def _phase_anchor(phase: str) -> int | None:
    return PHASE_ANCHOR_MINUTES.get(str(phase or ""))


def turn_end_clock(record: dict[str, Any]) -> str:
    """End-of-turn clock derived from engine data."""
    pc = record.get("phase_clock") or {}
    phase = str(pc.get("phase") or record.get("phase") or "")
    elapsed = pc.get("elapsed_minutes")
    anchor = _phase_anchor(phase)
    if anchor is None or not isinstance(elapsed, (int, float)):
        return ""
    return _fmt_clock(anchor + int(elapsed))


def turn_start_clock(record: dict[str, Any]) -> str:
    """Start-of-turn clock derived from engine data."""
    pc = record.get("phase_clock") or {}
    phase = str(pc.get("phase") or record.get("phase") or "")
    elapsed = pc.get("elapsed_minutes")
    anchor = _phase_anchor(phase)
    if anchor is None or not isinstance(elapsed, (int, float)):
        return ""
    cost = record.get("time_cost") or 0
    if not isinstance(cost, (int, float)):
        cost = 0
    return _fmt_clock(anchor + max(0, int(elapsed) - int(cost)))


def scene_clock_range(records: list[dict[str, Any]]) -> str:
    """Format a HH:MM-HH:MM window covering this scene."""
    if not records:
        return ""
    first_start = turn_start_clock(records[0])
    last_end = turn_end_clock(records[-1])
    if not first_start and not last_end:
        return ""
    if first_start and last_end and first_start != last_end:
        return f"{first_start}-{last_end}"
    return first_start or last_end
