"""Feature-coverage evaluation for recorded playthrough traces."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

EXIT_INTENTS = {"end_softly", "walk_away", "change_subject_and_drift"}
FLIRTY_INTENTS = {"escalate_flirt"}
BANTER_INTENTS = {"joke_back", "deflect_with_humor"}
DEEP_INTENTS = {"go_deeper", "honest_vulnerable"}
SUPPORTIVE_INTENTS = {"apologize"}
FRIENDLY_INTENTS = {"ask_about_topic", "change_subject", "defend_self"}


class PlaythroughAssertion(BaseModel):
    """One binary feature-coverage assertion."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    passed: bool
    detail: str
    interesting_turns: list[int] = Field(default_factory=list)


class PlaythroughStats(BaseModel):
    """Aggregate numbers used by the review dashboard."""

    model_config = ConfigDict(extra="forbid")

    turns: int
    conversations_started: int
    wheel_exits: int
    walk_aways: int
    pull_attempts: int
    pull_failures: int
    interruptions_fired: int
    interruption_responses: int
    interruption_response_kinds: list[str] = Field(default_factory=list)
    memories_created: int
    background_dialogues: int
    gossip_picks: int
    low_chance_rolls: int
    ceremony_events: int
    audience_snapshots: int
    outcome: str | None = None
    success_rate_by_category: dict[str, str] = Field(default_factory=dict)


class PlaythroughReport(BaseModel):
    """Structured report for a recorded playthrough."""

    model_config = ConfigDict(extra="forbid")

    trace_path: str
    passed: int
    failed: int
    stats: PlaythroughStats
    assertions: list[PlaythroughAssertion]
    interesting_turns: list[int] = Field(default_factory=list)


def evaluate_trace_file(path: Path) -> PlaythroughReport:
    """Load and evaluate a recorded playthrough package."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"playthrough trace must be a JSON object: {path}")
    return evaluate_trace(payload, trace_path=str(path))


def evaluate_trace(package: dict[str, Any], *, trace_path: str = "<memory>") -> PlaythroughReport:
    """Evaluate feature coverage in a recorded playthrough package."""
    records = package.get("records")
    if not isinstance(records, list):
        raise ValueError("playthrough trace requires a records list")
    typed_records = [record for record in records if isinstance(record, dict)]
    final_state = package.get("final_state")
    stats = _stats(typed_records, final_state if isinstance(final_state, dict) else None)
    assertions = _assertions(typed_records, stats)
    interesting = sorted(
        {
            turn
            for assertion in assertions
            for turn in assertion.interesting_turns
        }
    )
    passed = sum(1 for assertion in assertions if assertion.passed)
    failed = len(assertions) - passed
    return PlaythroughReport(
        trace_path=trace_path,
        passed=passed,
        failed=failed,
        stats=stats,
        assertions=assertions,
        interesting_turns=interesting,
    )


def _stats(records: list[dict[str, Any]], final_state: dict[str, Any] | None) -> PlaythroughStats:
    category_success: dict[str, Counter[str]] = defaultdict(Counter)
    conversations_started = 0
    wheel_exits = 0
    walk_aways = 0
    pull_attempts = 0
    pull_failures = 0
    interruptions_fired = 0
    interruption_responses = 0
    interruption_response_kinds: set[str] = set()
    memories_created = 0
    background_dialogues = 0
    gossip_picks = 0
    low_chance_rolls = 0
    ceremony_events = 0
    audience_snapshots = 0

    for record in records:
        action = _dict(record.get("action"))
        result = _dict(record.get("mechanical_result"))
        result_action = _dict(result.get("action"))
        commits = _dict(record.get("agent_commits"))
        villa_update = _dict(commits.get("villa_update"))
        pull = result.get("pull_attempt")
        turn = _turn(record)

        kind = str(action.get("kind", ""))
        intent_id = str(action.get("intent_id", "") or result_action.get("intent_id", ""))
        category = _record_category(record)
        if category:
            category_success[category]["success" if result.get("success") is True else "miss"] += 1
        if kind == "start_conversation":
            conversations_started += 1
        if kind == "respond_with" and category == "exit":
            wheel_exits += 1
        if kind == "end_conversation":
            walk_aways += 1
        if isinstance(pull, dict):
            pull_attempts += 1
            if pull.get("success") is False:
                pull_failures += 1
        interruptions = villa_update.get("npc_interruptions")
        if isinstance(interruptions, list):
            interruptions_fired += len(interruptions)
        if intent_id in {"accept_interruption", "defer_interruption", "ignore_interruption"}:
            interruption_responses += 1
            interruption_response_kinds.add(intent_id)
        batches = commits.get("curator_batches")
        if isinstance(batches, list):
            for batch in batches:
                memories = _dict(batch).get("memories")
                if isinstance(memories, list):
                    memories_created += len(memories)
        dialogues = commits.get("background_dialogues")
        if isinstance(dialogues, list):
            background_dialogues += len(dialogues)
        if category == "gossip" and kind == "respond_with":
            gossip_picks += 1
        chance = result.get("success_chance")
        roll = result.get("roll")
        if isinstance(chance, int) and isinstance(roll, int) and chance < 60:
            low_chance_rolls += 1
        events = record.get("ceremony_events")
        if isinstance(events, list):
            ceremony_events += len(events)
        if isinstance(record.get("audience_snapshot"), dict):
            audience_snapshots += 1
        if turn < 0:
            raise ValueError("recorded turn must be non-negative")

    success_rate_by_category = {
        category: _format_rate(counts["success"], counts["success"] + counts["miss"])
        for category, counts in sorted(category_success.items())
    }
    return PlaythroughStats(
        turns=len(records),
        conversations_started=conversations_started,
        wheel_exits=wheel_exits,
        walk_aways=walk_aways,
        pull_attempts=pull_attempts,
        pull_failures=pull_failures,
        interruptions_fired=interruptions_fired,
        interruption_responses=interruption_responses,
        interruption_response_kinds=sorted(interruption_response_kinds),
        memories_created=memories_created,
        background_dialogues=background_dialogues,
        gossip_picks=gossip_picks,
        low_chance_rolls=low_chance_rolls,
        ceremony_events=ceremony_events,
        audience_snapshots=audience_snapshots,
        outcome=_final_outcome(final_state),
        success_rate_by_category=success_rate_by_category,
    )


def _assertions(
    records: list[dict[str, Any]],
    stats: PlaythroughStats,
) -> list[PlaythroughAssertion]:
    memory_holders = _memory_holder_counts(records)
    return [
        _assert("wheel_exit", "At least one graceful wheel exit", stats.wheel_exits >= 1, f"{stats.wheel_exits} wheel exit(s)", _turns_with_category(records, "exit")),
        _assert("walk_away", "At least one curt walk-away", stats.walk_aways >= 1, f"{stats.walk_aways} walk-away action(s)", _turns_with_action(records, "end_conversation")),
        _assert("pull_attempt", "At least one pull-for-chat attempt", stats.pull_attempts >= 1, f"{stats.pull_attempts} pull attempt(s)", _turns_with_pull(records)),
        _assert("pull_failure", "At least one failed pull attempt", stats.pull_failures >= 1, f"{stats.pull_failures} failed pull(s)", _turns_with_pull(records, success=False)),
        _assert("interruption_fired", "At least one NPC interruption fired", stats.interruptions_fired >= 1, f"{stats.interruptions_fired} interruption(s)", _turns_with_interruption(records)),
        _assert(
            "interruption_answered",
            "At least two interruption response kinds were exercised",
            len(stats.interruption_response_kinds) >= 2,
            f"{stats.interruption_responses} response(s): {', '.join(stats.interruption_response_kinds) or 'none'}",
            _turns_with_interruption_response(records),
        ),
        _assert("memory_coverage", "Each major NPC has at least three memories", all(memory_holders.get(npc_id, 0) >= 3 for npc_id in ("chloe", "maya", "liam")), f"memory counts: {dict(memory_holders)}", _turns_with_memories(records)),
        _assert("low_chance_rolls", "At least three rolls below sixty percent", stats.low_chance_rolls >= 3, f"{stats.low_chance_rolls} low-chance roll(s)", _turns_with_low_chance(records)),
        _assert("gossip_pick", "At least one gossip option was picked", stats.gossip_picks >= 1, f"{stats.gossip_picks} gossip pick(s)", _turns_with_category(records, "gossip")),
        _assert("ceremony_event_observed", "At least one ceremony or bombshell event occurred", stats.ceremony_events >= 1, f"{stats.ceremony_events} ceremony event(s)", _turns_with_ceremony(records)),
        _assert("background_life", "Background NPC dialogue happened", stats.background_dialogues >= 1, f"{stats.background_dialogues} background exchange(s)", _turns_with_background(records)),
        _assert("outcome_assigned", "Run has a defined outcome", stats.outcome is not None, f"outcome: {stats.outcome or 'none'}", _turns_with_outcome(records)),
        _assert("audience_ranking_per_day", "Audience rankings were recorded", stats.audience_snapshots >= 1, f"{stats.audience_snapshots} audience snapshot(s)", _turns_with_audience(records)),
    ]


def _assert(
    assertion_id: str,
    label: str,
    passed: bool,
    detail: str,
    turns: list[int],
) -> PlaythroughAssertion:
    return PlaythroughAssertion(
        id=assertion_id,
        label=label,
        passed=passed,
        detail=detail,
        interesting_turns=turns[:8],
    )


def _memory_holder_counts(records: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for record in records:
        commits = _dict(record.get("agent_commits"))
        batches = commits.get("curator_batches")
        if not isinstance(batches, list):
            continue
        for batch in batches:
            memories = _dict(batch).get("memories")
            if not isinstance(memories, list):
                continue
            for raw_memory in memories:
                holder = _dict(raw_memory).get("holder_id")
                if isinstance(holder, str):
                    counts[holder] += 1
    return counts


def _turns_with_action(records: list[dict[str, Any]], kind: str) -> list[int]:
    return [_turn(record) for record in records if _dict(record.get("action")).get("kind") == kind]


def _turns_with_category(records: list[dict[str, Any]], category: str) -> list[int]:
    return [
        _turn(record)
        for record in records
        if _record_category(record) == category
    ]


def _turns_with_pull(records: list[dict[str, Any]], *, success: bool | None = None) -> list[int]:
    turns: list[int] = []
    for record in records:
        pull = _dict(record.get("mechanical_result")).get("pull_attempt")
        if not isinstance(pull, dict):
            continue
        if success is None or pull.get("success") is success:
            turns.append(_turn(record))
    return turns


def _turns_with_interruption(records: list[dict[str, Any]]) -> list[int]:
    turns: list[int] = []
    for record in records:
        villa_update = _dict(_dict(record.get("agent_commits")).get("villa_update"))
        interruptions = villa_update.get("npc_interruptions")
        if isinstance(interruptions, list) and interruptions:
            turns.append(_turn(record))
    return turns


def _turns_with_interruption_response(records: list[dict[str, Any]]) -> list[int]:
    intents = {"accept_interruption", "defer_interruption", "ignore_interruption"}
    return [
        _turn(record)
        for record in records
        if str(_dict(record.get("action")).get("intent_id", "")) in intents
    ]


def _turns_with_memories(records: list[dict[str, Any]]) -> list[int]:
    turns: list[int] = []
    for record in records:
        commits = _dict(record.get("agent_commits"))
        if commits.get("curator_batches"):
            turns.append(_turn(record))
    return turns


def _turns_with_low_chance(records: list[dict[str, Any]]) -> list[int]:
    turns: list[int] = []
    for record in records:
        result = _dict(record.get("mechanical_result"))
        chance = result.get("success_chance")
        roll = result.get("roll")
        if isinstance(chance, int) and isinstance(roll, int) and chance < 60:
            turns.append(_turn(record))
    return turns


def _turns_with_background(records: list[dict[str, Any]]) -> list[int]:
    turns: list[int] = []
    for record in records:
        dialogues = _dict(record.get("agent_commits")).get("background_dialogues")
        if isinstance(dialogues, list) and dialogues:
            turns.append(_turn(record))
    return turns


def _turns_with_ceremony(records: list[dict[str, Any]]) -> list[int]:
    turns: list[int] = []
    for record in records:
        events = record.get("ceremony_events")
        if isinstance(events, list) and events:
            turns.append(_turn(record))
    return turns


def _turns_with_audience(records: list[dict[str, Any]]) -> list[int]:
    return [_turn(record) for record in records if isinstance(record.get("audience_snapshot"), dict)]


def _turns_with_outcome(records: list[dict[str, Any]]) -> list[int]:
    return [
        _turn(record)
        for record in records
        if any(_dict(event).get("kind") == "final_vote" for event in _list(record.get("ceremony_events")))
    ]


def _final_outcome(final_state: dict[str, Any] | None) -> str | None:
    outcome = None if final_state is None else final_state.get("outcome")
    return outcome if isinstance(outcome, str) else None


def _record_category(record: dict[str, Any]) -> str | None:
    action = _dict(record.get("action"))
    if action.get("kind") != "respond_with":
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


def _format_rate(successes: int, total: int) -> str:
    if total == 0:
        return "0/0"
    return f"{successes}/{total} ({round((successes / total) * 100)}%)"


def _turn(record: dict[str, Any]) -> int:
    turn = record.get("turn")
    return turn if isinstance(turn, int) else -1

def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
