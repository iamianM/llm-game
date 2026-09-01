"""Typed contracts for golden LLM eval scenarios."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.eval.golden_costs import RunAccounting
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
CheckSeverity = Literal["blocking", "advisory"]
ExecutionModel = Literal["isolated_golden_replay", "causal_rollout"]
EvalCategory = Literal[
    "conversation",
    "social_dynamics",
    "pairing_and_endings",
    "special_events",
    "challenges",
]


class ThreadCriterion(BaseModel):
    """One authored dimension inside the scenario's holistic thread check."""

    model_config = ConfigDict(extra="forbid")

    id: str
    criteria: str
    pass_examples: list[str] = Field(default_factory=list)
    fail_examples: list[str] = Field(default_factory=list)


class ThreadCheckSpec(BaseModel):
    """The single holistic semantic check for a complete scenario thread."""

    model_config = ConfigDict(extra="forbid")

    id: str = "thread_acceptance"
    severity: CheckSeverity = "blocking"
    criteria: list[ThreadCriterion] = Field(min_length=1)


class GoldenAgentResult(BaseModel):
    """One reviewed output reference in the same shape as the agent result."""

    model_config = ConfigDict(extra="forbid")

    agent: str
    output_type: str
    output: dict[str, Any]


class GoldenTurnTarget(BaseModel):
    """Reviewed expected agent results in actual-result shape."""

    model_config = ConfigDict(extra="forbid")

    calls: list[GoldenAgentResult] = Field(default_factory=list)


class GoldenTurnSpec(BaseModel):
    """One action plus authored expectations."""

    model_config = ConfigDict(extra="forbid")

    id: str
    action: PlayerAction
    arrange_player_location: Location | None = None
    arrange_npc_locations: dict[str, Location] = Field(default_factory=dict)
    arrange_active_conversation: Conversation | None = None
    golden: GoldenTurnTarget
    checks: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_stable_follow_up_selection(self) -> GoldenTurnSpec:
        """Keep generated-menu evals stable by selecting a semantic intent."""
        if self.action.kind is ActionKind.RESPOND_WITH and self.action.option_index is not None:
            raise ValueError(
                "golden eval RESPOND_WITH actions must select intent_id, not option_index"
            )
        return self


class JudgeCriterionFinding(BaseModel):
    """Judge verdict and cited evidence for one authored thread criterion."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    result: CheckResultValue
    reason: str
    evidence: str | None = None


class GoldenEvalScenario(BaseModel):
    """One runnable golden eval scenario."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    question: str
    category: EvalCategory
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
    thread_check: ThreadCheckSpec
    causal_thread_check: ThreadCheckSpec | None = None
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
    severity: CheckSeverity = "blocking"
    criterion_findings: list[JudgeCriterionFinding] = Field(default_factory=list)


class JudgeTrace(BaseModel):
    """Reviewable metadata for the single thread-level judge call."""

    model_config = ConfigDict(extra="forbid")

    model: str
    reasoning_effort: str
    prompt_path: str
    latency_ms: int
    response_id: str | None = None
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    cache_write_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    total_tokens: int | None = None
    attempts: int = 1
    retry_errors: list[str] = Field(default_factory=list)
    reasoning_summaries: list[str] = Field(default_factory=list)


class GoldenTurnResult(BaseModel):
    """Review payload for one evaluated turn."""

    model_config = ConfigDict(extra="forbid")

    id: str
    action: dict[str, Any]
    arrangements: dict[str, Any] = Field(default_factory=dict)
    input_source: Literal["fresh_scenario_state", "reviewed_prefix", "actual_prefix"]
    input_turn_ids: list[str] = Field(default_factory=list)
    golden: GoldenTurnTarget
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
    question: str
    category: EvalCategory
    goal: str
    status: CheckResultValue
    thread_expectation: ThreadCheckSpec
    thread_check: GoldenCheckResult | None = None
    judge_trace: JudgeTrace | None = None
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
    accounting: RunAccounting
    scenarios: list[GoldenScenarioResult]
    execution_model: ExecutionModel = "isolated_golden_replay"
