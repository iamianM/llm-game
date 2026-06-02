"""Typed contracts for golden LLM eval scenarios."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.game.engine.actions import PlayerAction
from src.game.state.models import (
    CharacterCreation,
    Conversation,
    Couple,
    Location,
    NPCNPCConversation,
    Phase,
    PlayerStats,
    RelationshipState,
)

CheckResultValue = Literal["pass", "fail", "cannot_determine"]


class JudgeCheckSpec(BaseModel):
    """One semantic check evaluated by an optional LLM judge."""

    model_config = ConfigDict(extra="forbid")

    id: str
    criteria: str
    pass_examples: list[str] = Field(default_factory=list)
    fail_examples: list[str] = Field(default_factory=list)


class GoldenTurnSpec(BaseModel):
    """One action plus authored expectations."""

    model_config = ConfigDict(extra="forbid")

    id: str
    action: PlayerAction
    arrange_player_location: Location | None = None
    arrange_npc_locations: dict[str, Location] = Field(default_factory=dict)
    arrange_active_conversation: Conversation | None = None
    golden: str | None = None
    checks: list[str] = Field(default_factory=list)
    judge_checks: list[JudgeCheckSpec] = Field(default_factory=list)


class GoldenEvalScenario(BaseModel):
    """One runnable golden eval scenario."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    goal: str
    seed: int
    player_stats: PlayerStats | None = None
    character_creation: CharacterCreation | None = None
    initial_day: int | None = Field(default=None, ge=1, le=6)
    initial_phase: Phase | None = None
    initial_phase_budget_minutes: int | None = Field(default=None, ge=0, le=480)
    initial_location: Location | None = None
    initial_relationships: dict[str, RelationshipState] | None = None
    initial_couples: list[Couple] | None = None
    initial_npc_conversations: list[NPCNPCConversation] | None = None
    live_resort_life: bool = False
    judge_context: list[str] = Field(default_factory=list)
    turns: list[GoldenTurnSpec] = Field(min_length=1)


class GoldenCheckResult(BaseModel):
    """Result of one deterministic or judge check."""

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Literal["deterministic", "judge"]
    result: CheckResultValue
    reason: str
    evidence: str | None = None
    turn_id: str | None = None


class GoldenTurnResult(BaseModel):
    """Review payload for one evaluated turn."""

    model_config = ConfigDict(extra="forbid")

    id: str
    action: dict[str, Any]
    arrangements: dict[str, Any] = Field(default_factory=dict)
    expected_tools: list[str] = Field(default_factory=list)
    golden: str | None = None
    judge_checks: list[JudgeCheckSpec] = Field(default_factory=list)
    input_hash: str
    output_hash: str | None = None
    record: dict[str, Any] | None = None
    checks: list[GoldenCheckResult] = Field(default_factory=list)
    error: str | None = None


class GoldenScenarioResult(BaseModel):
    """Review payload for one scenario."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    goal: str
    status: CheckResultValue
    turns: list[GoldenTurnResult] = Field(default_factory=list)


class GoldenEvalRun(BaseModel):
    """Full golden eval run artifact."""

    model_config = ConfigDict(extra="forbid")

    llm_mode: Literal["mock", "real"]
    judge_enabled: bool
    scenario_count: int
    worker_count: int
    passed: int
    failed: int
    cannot_determine: int
    scenarios: list[GoldenScenarioResult]
