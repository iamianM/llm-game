"""Pydantic models for playthrough evaluation reports."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PlaythroughAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    passed: bool
    detail: str
    interesting_turns: list[int] = Field(default_factory=list)


class PlaythroughStats(BaseModel):
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
    challenges_completed: int = 0
    challenges_succeeded: int = 0
    producer_texts_fired: int = 0
    group_dates_held: int = 0
    revealed_preference_count: int = 0
    compatibility_bonus_observed: int = 0
    max_couple_strength_reached: int = 0
    hideaway_used: bool = False
    steal_attempts_total: int = 0
    steal_successes: int = 0
    casa_amor_visited: bool = False
    casa_amor_player_decision: str | None = None
    casa_amor_partners_swapped: bool = False
    casa_amor_perception_swing: int = 0
    autopilot_actions_total: int = 0
    autopilot_rationales_present: int = 0
    autopilot_confidence_counts: dict[str, int] = Field(default_factory=dict)
    auto_advances_total: int = 0
    avg_actions_per_phase: float = 0.0
    arrival_rolls_total: int = 0
    arrival_interrupt_hits: int = 0
    arrival_pull_hits: int = 0
    npc_summoned_total: int = 0
    npc_left_total: int = 0
    final_day: int = 0
    outcome: str | None = None
    success_rate_by_category: dict[str, str] = Field(default_factory=dict)


class PlaythroughReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_path: str
    passed: int
    failed: int
    stats: PlaythroughStats
    assertions: list[PlaythroughAssertion]
    interesting_turns: list[int] = Field(default_factory=list)
