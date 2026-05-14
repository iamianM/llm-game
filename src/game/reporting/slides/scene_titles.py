"""Title helpers for slide scene rendering."""

from __future__ import annotations

from typing import Any


def _ceremony_title(kind: str, day: Any = None) -> str:
    if kind == "recoupling" and day == 1:
        return "Opening Coupling"
    return {
        "recoupling": "Recoupling Ceremony",
        "bombshell": "Bombshell Arrival",
        "elimination": "Elimination",
        "casa_amor_announce": "Casa Amor Announcement",
        "casa_amor_arrival": "Casa Amor Arrival",
        "casa_amor_decision": "Casa Amor Decision",
        "casa_amor_return_reveal": "Casa Amor Return",
        "final_vote": "🏆 Finale",
        "producer_text": "I've got a text",
        "gather_scheduled": "Everyone gathers",
        "challenge": "Challenge",
    }.get(kind, kind.replace("_", " ").title())


def _challenge_title(kind: str) -> str:
    return {
        "compatibility_quiz": "Compatibility Quiz",
        "heart_rate": "Heart Rate Challenge",
        "mr_and_mrs": "Mr & Mrs",
        "lie_detector": "Lie Detector",
        "snog_marry_pie": "Snog, Marry, Pie",
        "final_couples": "Final Couples Challenge",
    }.get(kind, kind.replace("_", " ").title())


def _conversation_target(records: list[dict[str, Any]]) -> str:
    for record in records:
        action = record.get("mechanical_result", {}).get("action", {})
        target = action.get("target_id")
        if target:
            return str(target)
    return ""
