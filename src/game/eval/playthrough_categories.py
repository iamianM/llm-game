"""Conversation category helpers for playthrough evals."""

from __future__ import annotations

from typing import Any

EXIT_INTENTS = {"end_softly", "walk_away", "change_subject_and_drift"}
FLIRTY_INTENTS = {"escalate_flirt"}
BANTER_INTENTS = {"joke_back", "deflect_with_humor"}
DEEP_INTENTS = {"go_deeper", "honest_vulnerable"}
SUPPORTIVE_INTENTS = {"apologize"}
FRIENDLY_INTENTS = {"ask_about_topic", "change_subject", "defend_self"}


def record_category(record: dict[str, Any]) -> str | None:
    """Classify a recorded response action into an eval category."""
    action = record.get("action")
    if not isinstance(action, dict) or action.get("kind") != "respond_with":
        return None
    intent_id = action.get("intent_id")
    if not isinstance(intent_id, str):
        return None
    if intent_id in {"accept_interruption", "defer_interruption", "ignore_interruption"}:
        return "interruption"
    if intent_id.startswith("ask_gossip:"):
        return "gossip"
    if intent_id in EXIT_INTENTS:
        return "exit"
    if intent_id in FLIRTY_INTENTS:
        return "flirty"
    if intent_id in BANTER_INTENTS:
        return "banter"
    if intent_id in DEEP_INTENTS:
        return "deep"
    if intent_id in SUPPORTIVE_INTENTS:
        return "supportive"
    if intent_id in FRIENDLY_INTENTS:
        return "friendly"
    return None
