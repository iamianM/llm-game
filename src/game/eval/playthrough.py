"""Feature-coverage evaluation for recorded playthrough traces."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.game.eval.playthrough_categories import record_category
from src.game.eval.playthrough_models import (
    PlaythroughAssertion,
    PlaythroughReport,
    PlaythroughStats,
)
from src.game.eval.playthrough_trace import (
    as_dict,
    final_outcome,
    format_rate,
    memory_holder_counts,
    revealed_preference_count,
    turn,
    turns_with_action,
    turns_with_arrival_rolls,
    turns_with_audience,
    turns_with_auto_advance,
    turns_with_autopilot,
    turns_with_background,
    turns_with_casa_amor,
    turns_with_casa_return,
    turns_with_casa_swing,
    turns_with_category,
    turns_with_ceremony,
    turns_with_challenge,
    turns_with_compatibility,
    turns_with_couple_strength,
    turns_with_group_date,
    turns_with_hideaway,
    turns_with_interruption,
    turns_with_interruption_response,
    turns_with_low_chance,
    turns_with_memories,
    turns_with_npc_initiated_exit,
    turns_with_outcome,
    turns_with_phase_overage,
    turns_with_producer_text,
    turns_with_pull,
    turns_with_reveals,
    turns_with_steal_attempt,
)


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
    mode = package.get("mode")
    trace_mode = mode if isinstance(mode, str) else "manual"
    assertions = _assertions(typed_records, stats, trace_mode=trace_mode)
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
    challenges_completed = 0
    challenges_succeeded = 0
    producer_texts_fired = 0
    group_dates_held = 0
    compatibility_bonus_observed = 0
    max_couple_strength_reached = 0
    hideaway_used = False
    steal_attempts_total = 0
    steal_successes = 0
    casa_amor_visited = False
    casa_amor_player_decision: str | None = None
    casa_amor_partners_swapped = False
    casa_perception_before: int | None = None
    casa_perception_after: int | None = None
    autopilot_actions_total = 0
    autopilot_rationales_present = 0
    autopilot_confidence: Counter[str] = Counter()
    auto_advances_total = 0
    phase_counts: Counter[tuple[int, str]] = Counter()
    arrival_rolls_total = 0
    arrival_interrupt_hits = 0
    arrival_pull_hits = 0
    npc_summoned_total = 0
    npc_left_total = 0

    for record in records:
        action = as_dict(record.get("action"))
        result = as_dict(record.get("mechanical_result"))
        result_action = as_dict(result.get("action"))
        commits = as_dict(record.get("agent_commits"))
        villa_update = as_dict(commits.get("villa_update"))
        pull = result.get("pull_attempt")
        turn_number = turn(record)

        kind = str(action.get("kind", ""))
        day = record.get("day")
        phase = record.get("phase")
        if isinstance(day, int) and isinstance(phase, str):
            phase_counts[(day, phase)] += 1
        if record.get("auto_advance") is True:
            auto_advances_total += 1
        intent_id = str(action.get("intent_id", "") or result_action.get("intent_id", ""))
        category = record_category(record)
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
        summoned = villa_update.get("npc_summoned_elsewhere")
        if isinstance(summoned, list):
            npc_summoned_total += len(summoned)
        rolls = record.get("arrival_rolls")
        if isinstance(rolls, list):
            arrival_rolls_total += len(rolls)
            for arrival_roll in rolls:
                arrival = as_dict(arrival_roll)
                arrival_interrupt_hits += int(arrival.get("interruption_hit") is True)
                arrival_pull_hits += int(arrival.get("pull_hit") is True)
        follow_up_menu = as_dict(record.get("follow_up_menu"))
        if follow_up_menu.get("npc_will_leave") is True:
            npc_left_total += 1
        if intent_id in {"accept_interruption", "defer_interruption", "ignore_interruption"}:
            interruption_responses += 1
            interruption_response_kinds.add(intent_id)
        batches = commits.get("curator_batches")
        if isinstance(batches, list):
            for batch in batches:
                memories = as_dict(batch).get("memories")
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
            for event in events:
                if as_dict(event).get("kind") == "steal_attempt":
                    steal_attempts_total += 1
                    if "succeeds" in str(as_dict(event).get("message", "")):
                        steal_successes += 1
        if isinstance(record.get("audience_snapshot"), dict):
            audience_snapshots += 1
        challenge = record.get("challenge")
        if isinstance(challenge, dict) and challenge.get("result") in {"success", "failure"}:
            challenges_completed += 1
            if challenge.get("result") == "success":
                challenges_succeeded += 1
        if isinstance(record.get("producer_text"), dict):
            producer_texts_fired += 1
        group_date = record.get("group_date")
        if isinstance(group_date, dict):
            group_dates_held += 1
        breakdown = as_dict(result.get("chance_breakdown"))
        if isinstance(breakdown.get("compatibility_bonus"), int) and breakdown["compatibility_bonus"] > 0:
            compatibility_bonus_observed += 1
        strength = record.get("couple_strength")
        if isinstance(strength, int):
            max_couple_strength_reached = max(max_couple_strength_reached, strength)
        if kind == "hideaway":
            hideaway_used = True
        autopilot = as_dict(commits.get("player_autopilot"))
        if autopilot:
            autopilot_actions_total += 1
            rationale = autopilot.get("rationale")
            if isinstance(rationale, str) and rationale.strip():
                autopilot_rationales_present += 1
            confidence = autopilot.get("confidence")
            if isinstance(confidence, str):
                autopilot_confidence[confidence] += 1
        if record.get("villa") == "casa_amor":
            casa_amor_visited = True
        casa = record.get("casa_amor")
        if isinstance(casa, dict):
            decision = casa.get("player_decision")
            if isinstance(decision, str):
                casa_amor_player_decision = decision
            casa_amor_partners_swapped = casa_amor_partners_swapped or casa.get("partners_swapped") is True
            before = casa.get("player_perception_before")
            after = casa.get("player_perception_after")
            if isinstance(before, int):
                casa_perception_before = before
            if isinstance(after, int):
                casa_perception_after = after
        if turn_number < 0:
            raise ValueError("recorded turn must be non-negative")

    success_rate_by_category = {
        category: format_rate(counts["success"], counts["success"] + counts["miss"])
        for category, counts in sorted(category_success.items())
    }
    avg_actions_per_phase = (
        0.0 if not phase_counts else sum(phase_counts.values()) / len(phase_counts)
    )
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
        challenges_completed=challenges_completed,
        challenges_succeeded=challenges_succeeded,
        producer_texts_fired=producer_texts_fired,
        group_dates_held=group_dates_held,
        revealed_preference_count=revealed_preference_count(final_state),
        compatibility_bonus_observed=compatibility_bonus_observed,
        max_couple_strength_reached=max_couple_strength_reached,
        hideaway_used=hideaway_used,
        steal_attempts_total=steal_attempts_total,
        steal_successes=steal_successes,
        casa_amor_visited=casa_amor_visited,
        casa_amor_player_decision=casa_amor_player_decision,
        casa_amor_partners_swapped=casa_amor_partners_swapped,
        casa_amor_perception_swing=(
            0
            if casa_perception_before is None or casa_perception_after is None
            else casa_perception_after - casa_perception_before
        ),
        autopilot_actions_total=autopilot_actions_total,
        autopilot_rationales_present=autopilot_rationales_present,
        autopilot_confidence_counts=dict(autopilot_confidence),
        auto_advances_total=auto_advances_total,
        avg_actions_per_phase=round(avg_actions_per_phase, 2),
        arrival_rolls_total=arrival_rolls_total,
        arrival_interrupt_hits=arrival_interrupt_hits,
        arrival_pull_hits=arrival_pull_hits,
        npc_summoned_total=npc_summoned_total,
        npc_left_total=npc_left_total,
        outcome=final_outcome(final_state),
        success_rate_by_category=success_rate_by_category,
    )


def _assertions(
    records: list[dict[str, Any]],
    stats: PlaythroughStats,
    *,
    trace_mode: str,
) -> list[PlaythroughAssertion]:
    memory_holders = memory_holder_counts(records)
    return [
        _assert("wheel_exit", "At least one graceful wheel exit", stats.wheel_exits >= 1, f"{stats.wheel_exits} wheel exit(s)", turns_with_category(records, "exit")),
        _assert("walk_away", "At least one curt walk-away", stats.walk_aways >= 1, f"{stats.walk_aways} walk-away action(s)", turns_with_action(records, "end_conversation")),
        _assert("pull_attempt", "At least one pull-for-chat attempt", stats.pull_attempts >= 1, f"{stats.pull_attempts} pull attempt(s)", turns_with_pull(records)),
        _assert("pull_failure", "At least one failed pull attempt", stats.pull_failures >= 1, f"{stats.pull_failures} failed pull(s)", turns_with_pull(records, success=False)),
        _assert("interruption_fired", "At least one NPC interruption fired", stats.interruptions_fired >= 1, f"{stats.interruptions_fired} interruption(s)", turns_with_interruption(records)),
        _assert(
            "interruption_answered",
            "At least two interruption response kinds were exercised",
            len(stats.interruption_response_kinds) >= 2,
            f"{stats.interruption_responses} response(s): {', '.join(stats.interruption_response_kinds) or 'none'}",
            turns_with_interruption_response(records),
        ),
        _assert("memory_coverage", "Each major NPC has at least three memories", all(memory_holders.get(npc_id, 0) >= 3 for npc_id in ("chloe", "maya", "liam")), f"memory counts: {dict(memory_holders)}", turns_with_memories(records)),
        _assert("low_chance_rolls", "At least three rolls below sixty percent", stats.low_chance_rolls >= 3, f"{stats.low_chance_rolls} low-chance roll(s)", turns_with_low_chance(records)),
        _assert("gossip_pick", "At least one gossip option was picked", stats.gossip_picks >= 1, f"{stats.gossip_picks} gossip pick(s)", turns_with_category(records, "gossip")),
        _assert("ceremony_event_observed", "At least one ceremony or bombshell event occurred", stats.ceremony_events >= 1, f"{stats.ceremony_events} ceremony event(s)", turns_with_ceremony(records)),
        _assert("background_life", "Background NPC dialogue happened", stats.background_dialogues >= 1, f"{stats.background_dialogues} background exchange(s)", turns_with_background(records)),
        _assert("outcome_assigned", "Run has a defined outcome", stats.outcome is not None, f"outcome: {stats.outcome or 'none'}", turns_with_outcome(records)),
        _assert("audience_ranking_per_day", "Audience rankings were recorded", stats.audience_snapshots >= 1, f"{stats.audience_snapshots} audience snapshot(s)", turns_with_audience(records)),
        _assert("challenge_fired_each_day", "At least five daily challenges completed", stats.challenges_completed >= 5, f"{stats.challenges_completed} challenge(s)", turns_with_challenge(records)),
        _assert("producer_texts_fired", "At least three producer texts fired", stats.producer_texts_fired >= 3, f"{stats.producer_texts_fired} producer text(s)", turns_with_producer_text(records)),
        _assert("group_date_observed", "At least one group date was scheduled", stats.group_dates_held >= 1, f"{stats.group_dates_held} group date turn(s)", turns_with_group_date(records)),
        _assert("type_on_paper_revealed", "At least one Type on Paper bit was revealed", stats.revealed_preference_count >= 1, f"{stats.revealed_preference_count} revealed bit(s)", turns_with_reveals(records)),
        _assert("compatibility_bonus_observed", "At least one roll used compatibility bonus", stats.compatibility_bonus_observed >= 1, f"{stats.compatibility_bonus_observed} compatibility roll(s)", turns_with_compatibility(records)),
        _assert("couple_strength_visible", "Couple strength surfaced in the trace", stats.max_couple_strength_reached >= 1, f"max couple strength {stats.max_couple_strength_reached}", turns_with_couple_strength(records)),
        _assert("hideaway_used_when_eligible", "Hideaway was used after reaching high couple strength", stats.max_couple_strength_reached < 70 or stats.hideaway_used, f"hideaway used: {stats.hideaway_used}", turns_with_hideaway(records)),
        _assert("steal_attempt_observed", "At least one bombshell steal attempt occurred", stats.steal_attempts_total >= 1, f"{stats.steal_attempts_total} steal attempt(s), {stats.steal_successes} success(es)", turns_with_steal_attempt(records)),
        _assert("casa_amor_phase_observed", "Casa Amor phase was observed", stats.casa_amor_visited, f"visited: {stats.casa_amor_visited}", turns_with_casa_amor(records)),
        _assert("casa_amor_return_resolved", "Casa Amor return was resolved", stats.casa_amor_player_decision is not None, f"decision: {stats.casa_amor_player_decision or 'none'}", turns_with_casa_return(records)),
        _assert("casa_amor_perception_swing", "Casa Amor created a major perception swing", abs(stats.casa_amor_perception_swing) >= 6, f"swing: {stats.casa_amor_perception_swing}", turns_with_casa_swing(records)),
        _assert("autopilot_outcome_assigned", "Autopilot run reached a terminal outcome", trace_mode != "autopilot" or stats.outcome is not None, f"mode: {trace_mode}; outcome: {stats.outcome or 'none'}", turns_with_outcome(records)),
        _assert("autopilot_rationale_present", "Autopilot turns include rationales", trace_mode != "autopilot" or (stats.autopilot_actions_total > 0 and stats.autopilot_actions_total == stats.autopilot_rationales_present), f"{stats.autopilot_rationales_present}/{stats.autopilot_actions_total} rationale(s)", turns_with_autopilot(records)),
        _assert("phase_action_count_reasonable", "Average actions per phase is reasonable", stats.avg_actions_per_phase <= 12, f"avg actions/phase: {stats.avg_actions_per_phase}", turns_with_phase_overage(records)),
        _assert("time_expired_advance_observed", "At least one phase advanced because time expired", stats.auto_advances_total >= 1, f"{stats.auto_advances_total} auto-advance turn(s)", turns_with_auto_advance(records)),
        _assert("npc_initiated_exit_observed", "At least one NPC initiated an exit", stats.npc_summoned_total + stats.npc_left_total >= 1, f"{stats.npc_summoned_total} summon(s), {stats.npc_left_total} npc-left menu(s)", turns_with_npc_initiated_exit(records)),
        _assert("npc_arrival_rolls_observed", "At least two arrival rolls were recorded", stats.arrival_rolls_total >= 2, f"{stats.arrival_rolls_total} arrival roll(s)", turns_with_arrival_rolls(records)),
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
