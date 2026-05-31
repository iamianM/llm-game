"""Player-facing Paradise Hearts display translations."""

from __future__ import annotations

DISPLAY_NAMES: dict[str, str] = {
    "audience_appeal": "Heart Beats",
    "bombshell": "Heart Throb",
    "casa_amor": "Flush of Hearts",
    "casa_amor_announce": "Flush of Hearts Announcement",
    "casa_amor_arrival": "Flush of Hearts Arrival",
    "casa_amor_decision": "Flush of Hearts Decision",
    "casa_amor_return_reveal": "Sunset Bay Return",
    "casa_return": "Sunset Bay Return",
    "casa_pool": "Flush of Hearts Pool",
    "casa_kitchen": "Flush of Hearts Kitchen",
    "casa_terrace": "Flush of Hearts Terrace",
    "challenge": "Challenge",
    "compatibility_quiz": "Compatibility Quiz",
    "complete": "Complete",
    "evening": "Evening",
    "elimination": "Heart Out",
    "firepit": "Firepit",
    "final_couples": "Final Couples Challenge",
    "graft": "Spark",
    "heart_rate": "Pulse Race",
    "hideaway": "Paradise Suite",
    "intros": "Arrivals",
    "kitchen": "Kitchen",
    "lie_detector": "Lie Detector",
    "morning": "Morning",
    "main": "Sunset Bay",
    "mr_and_mrs": "The Couples Quiz",
    "opening": "First Spark",
    "pool": "Pool",
    "proposal": "Heart Swap Proposal",
    "producer_text": "Paradise Calls",
    "public_perception": "Pulse",
    "recouple": "Heart Swap",
    "recouple_proposal": "Heart Swap Proposal",
    "recoupling": "Pairing Ceremony",
    "snog_marry_pie": "Kiss Wed Pass",
    "text": "Paradise Calls",
    "terrace": "Terrace",
}


def display(value: str) -> str:
    """Return Paradise Hearts copy for an engine identifier."""
    return DISPLAY_NAMES.get(value, value.replace("_", " ").title())
