"""Player-facing Paradise Hearts display translations."""

from __future__ import annotations

DISPLAY_NAMES: dict[str, str] = {
    "audience_appeal": "Heart Beats",
    "heart_throb": "Heart Throb",
    "flush_of_hearts": "Flush of Hearts",
    "flush_of_hearts_announce": "Flush of Hearts Announcement",
    "flush_of_hearts_arrival": "Flush of Hearts Arrival",
    "flush_of_hearts_decision": "Flush of Hearts Decision",
    "flush_of_hearts_return_reveal": "Sunset Bay Return",
    "flush_return": "Sunset Bay Return",
    "flush_pool": "Flush of Hearts Pool",
    "flush_kitchen": "Flush of Hearts Kitchen",
    "flush_terrace": "Flush of Hearts Terrace",
    "challenge": "Challenge",
    "compatibility_quiz": "Compatibility Quiz",
    "complete": "Complete",
    "evening": "Evening",
    "elimination": "Heart Out",
    "flame_deck": "Flame Deck",
    "final_couples": "Final Couples Challenge",
    "spark": "Spark",
    "heart_rate": "Pulse Race",
    "private_suite": "Paradise Suite",
    "intros": "Arrivals",
    "kitchen": "Kitchen",
    "lie_detector": "Lie Detector",
    "morning": "Morning",
    "main": "Sunset Bay",
    "couples_quiz": "The Couples Quiz",
    "opening": "First Spark",
    "pool": "Pool",
    "proposal": "Heart Swap Proposal",
    "producer_text": "Paradise Calls",
    "public_perception": "Pulse",
    "pair": "Heart Swap",
    "pair_proposal": "Heart Swap Proposal",
    "pairing": "Pairing Ceremony",
    "kiss_wed_pass": "Kiss Wed Pass",
    "text": "Paradise Calls",
    "terrace": "Terrace",
}


def display(value: str) -> str:
    """Return Paradise Hearts copy for an engine identifier."""
    return DISPLAY_NAMES.get(value, value.replace("_", " ").title())
