"""Trace helper functions for playthrough evals."""

from __future__ import annotations

from typing import Any

from src.game.eval.playthrough_categories import record_category


def turns_with_action(records: list[dict[str, Any]], kind: str) -> list[int]:
    return [turn(record) for record in records if as_dict(record.get("action")).get("kind") == kind]


def turns_with_category(records: list[dict[str, Any]], category: str) -> list[int]:
    return [turn(record) for record in records if record_category(record) == category]


def turns_with_pull(records: list[dict[str, Any]], *, success: bool | None = None) -> list[int]:
    turns: list[int] = []
    for record in records:
        pull = as_dict(record.get("mechanical_result")).get("pull_attempt")
        if isinstance(pull, dict) and (success is None or pull.get("success") is success):
            turns.append(turn(record))
    return turns


def turns_with_interruption(records: list[dict[str, Any]]) -> list[int]:
    turns: list[int] = []
    for record in records:
        update = as_dict(as_dict(record.get("agent_commits")).get("villa_update"))
        interruptions = update.get("npc_interruptions")
        if isinstance(interruptions, list) and interruptions:
            turns.append(turn(record))
    return turns


def turns_with_interruption_response(records: list[dict[str, Any]]) -> list[int]:
    intents = {"accept_interruption", "defer_interruption", "ignore_interruption"}
    return [turn(record) for record in records if str(as_dict(record.get("action")).get("intent_id", "")) in intents]


def turns_with_memories(records: list[dict[str, Any]]) -> list[int]:
    return [turn(record) for record in records if as_dict(record.get("agent_commits")).get("curator_batches")]


def turns_with_low_chance(records: list[dict[str, Any]]) -> list[int]:
    turns: list[int] = []
    for record in records:
        result = as_dict(record.get("mechanical_result"))
        chance = result.get("success_chance")
        roll = result.get("roll")
        if isinstance(chance, int) and isinstance(roll, int) and chance < 60:
            turns.append(turn(record))
    return turns


def turns_with_background(records: list[dict[str, Any]]) -> list[int]:
    turns: list[int] = []
    for record in records:
        dialogues = as_dict(record.get("agent_commits")).get("background_dialogues")
        if isinstance(dialogues, list) and dialogues:
            turns.append(turn(record))
    return turns


def turns_with_ceremony(records: list[dict[str, Any]]) -> list[int]:
    return [turn(record) for record in records if as_list(record.get("ceremony_events"))]


def turns_with_audience(records: list[dict[str, Any]]) -> list[int]:
    return [turn(record) for record in records if isinstance(record.get("audience_snapshot"), dict)]


def turns_with_challenge(records: list[dict[str, Any]]) -> list[int]:
    return [turn(record) for record in records if isinstance(record.get("challenge"), dict)]


def turns_with_producer_text(records: list[dict[str, Any]]) -> list[int]:
    return [turn(record) for record in records if isinstance(record.get("producer_text"), dict)]


def turns_with_group_date(records: list[dict[str, Any]]) -> list[int]:
    return [turn(record) for record in records if isinstance(record.get("group_date"), dict)]


def turns_with_reveals(records: list[dict[str, Any]]) -> list[int]:
    return [turn(record) for record in records if as_dict(record.get("revealed_preferences"))]


def turns_with_compatibility(records: list[dict[str, Any]]) -> list[int]:
    turns: list[int] = []
    for record in records:
        breakdown = as_dict(as_dict(record.get("mechanical_result")).get("chance_breakdown"))
        if isinstance(breakdown.get("compatibility_bonus"), int) and breakdown["compatibility_bonus"] > 0:
            turns.append(turn(record))
    return turns


def turns_with_couple_strength(records: list[dict[str, Any]]) -> list[int]:
    return [turn(record) for record in records if isinstance(record.get("couple_strength"), int)]


def turns_with_hideaway(records: list[dict[str, Any]]) -> list[int]:
    return [turn(record) for record in records if as_dict(record.get("action")).get("kind") == "hideaway"]


def turns_with_steal_attempt(records: list[dict[str, Any]]) -> list[int]:
    return [
        turn(record)
        for record in records
        if any(as_dict(event).get("kind") == "steal_attempt" for event in as_list(record.get("ceremony_events")))
    ]


def turns_with_outcome(records: list[dict[str, Any]]) -> list[int]:
    return [
        turn(record)
        for record in records
        if any(as_dict(event).get("kind") == "final_vote" for event in as_list(record.get("ceremony_events")))
    ]


def final_outcome(final_state: dict[str, Any] | None) -> str | None:
    outcome = None if final_state is None else final_state.get("outcome")
    return outcome if isinstance(outcome, str) else None


def revealed_preference_count(final_state: dict[str, Any] | None) -> int:
    if final_state is None:
        return 0
    count = 0
    for islander in as_list(final_state.get("islanders")):
        familiarity = as_dict(islander).get("familiarity_with_player")
        if isinstance(familiarity, int):
            count += int(familiarity >= 25) + int(familiarity >= 50)
            count += int(familiarity >= 75) + int(familiarity >= 100)
    return count


def format_rate(successes: int, total: int) -> str:
    if total == 0:
        return "0/0"
    return f"{successes}/{total} ({round((successes / total) * 100)}%)"


def turn(record: dict[str, Any]) -> int:
    value = record.get("turn")
    return value if isinstance(value, int) else -1


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
