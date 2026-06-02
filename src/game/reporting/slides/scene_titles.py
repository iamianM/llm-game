"""Title helpers for slide scene rendering."""

from __future__ import annotations

from typing import Any


def _ceremony_title(kind: str, day: Any = None) -> str:
    if kind == "pairing" and day == 1:
        return "Opening Coupling"
    return {
        "pairing": "Pairing Ceremony",
        "heart_throb": "Heart Throb Arrival",
        "elimination": "Elimination",
        "flush_of_hearts_announce": "Flush of Hearts Announcement",
        "flush_of_hearts_arrival": "Flush of Hearts Arrival",
        "flush_of_hearts_decision": "Flush of Hearts Decision",
        "flush_of_hearts_return_reveal": "Sunset Bay Return",
        "final_vote": "Finale",
        "producer_text": "Paradise Calls",
        "gather_scheduled": "Everyone gathers",
        "challenge": "Challenge",
    }.get(kind, kind.replace("_", " ").title())


def _challenge_title(kind: str) -> str:
    return {
        "compatibility_quiz": "Compatibility Quiz",
        "heart_rate": "Heart Rate Challenge",
        "couples_quiz": "Couples Quiz",
        "lie_detector": "Lie Detector",
        "kiss_wed_pass": "Kiss, Wed, Pass",
        "final_couples": "Final Couples Challenge",
    }.get(kind, kind.replace("_", " ").title())


def _conversation_target(records: list[dict[str, Any]]) -> str:
    for record in records:
        action = record.get("mechanical_result", {}).get("action", {})
        target = action.get("target_id")
        if target:
            return str(target)
    return ""
