"""Safe public projection of a golden LLM eval run."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.game.eval.golden_costs import CostSummary, RunAccounting, summarize_call
from src.game.eval.golden_models import (
    CheckResultValue,
    EvalCategory,
    GoldenAgentResult,
    GoldenCheckResult,
    GoldenEvalRun,
    GoldenScenarioResult,
    GoldenTurnResult,
)


class ShowcaseCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Literal["deterministic", "judge"]
    result: CheckResultValue
    reason: str
    evidence: str | None = None


class ShowcaseTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: str
    model: str
    reasoning_effort: str
    output_type: str | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    cache_write_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    total_tokens: int | None = None
    cost: CostSummary | None = None
    output: Any = None
    reasoning_summaries: list[str] = Field(default_factory=list)
    attempt: int = 1


class ShowcaseGoldenCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: str
    output_type: str
    output: dict[str, Any]


class ShowcaseGolden(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criteria: str
    calls: list[ShowcaseGoldenCall] = Field(default_factory=list)


class ShowcaseDialogue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player: str
    npc: str
    tone: str | None = None
    mood_after: str | None = None


class ShowcaseChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    category: str
    risk: str


class ShowcaseStory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine_result: str | None = None
    relationship_changes: list[str] = Field(default_factory=list)
    dialogue: ShowcaseDialogue | None = None
    narration: str | None = None
    choices: list[ShowcaseChoice] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    memories: list[str] = Field(default_factory=list)
    resort_changes: str | None = None


class ShowcaseTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    action: str
    status: CheckResultValue
    golden: ShowcaseGolden
    story: ShowcaseStory
    checks: list[ShowcaseCheck] = Field(default_factory=list)
    traces: list[ShowcaseTrace] = Field(default_factory=list)


class ShowcaseJudge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: CheckResultValue
    reason: str
    evidence: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    cache_write_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    total_tokens: int | None = None
    cost: CostSummary | None = None
    reasoning_summaries: list[str] = Field(default_factory=list)
    criteria: list[str] = Field(default_factory=list)


class ShowcaseScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    question: str
    category: EvalCategory
    goal: str
    status: CheckResultValue
    judge: ShowcaseJudge | None = None
    turns: list[ShowcaseTurn]


class ShowcaseProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    published_at: str | None = None
    source_revision: str | None = None
    note: str | None = None


class GoldenEvalShowcase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[3] = 3
    llm_mode: Literal["mock", "real"]
    judge_enabled: bool
    passed: int
    failed: int
    cannot_determine: int
    turn_count: int
    agent_call_count: int
    total_tokens: int
    accounting: RunAccounting
    provenance: ShowcaseProvenance = Field(default_factory=ShowcaseProvenance)
    scenarios: list[ShowcaseScenario]


def build_golden_eval_showcase(run: GoldenEvalRun) -> GoldenEvalShowcase:
    """Project a raw run into an allowlisted, publication-safe artifact."""
    scenarios = [_scenario(result) for result in run.scenarios]
    traces = [trace for scenario in scenarios for turn in scenario.turns for trace in turn.traces]
    return GoldenEvalShowcase(
        llm_mode=run.llm_mode,
        judge_enabled=run.judge_enabled,
        passed=run.passed,
        failed=run.failed,
        cannot_determine=run.cannot_determine,
        turn_count=sum(len(scenario.turns) for scenario in scenarios),
        agent_call_count=len(traces),
        total_tokens=run.accounting.total.usage.total_tokens,
        accounting=run.accounting,
        scenarios=scenarios,
    )


def _scenario(result: GoldenScenarioResult) -> ShowcaseScenario:
    judge = None
    if result.thread_check is not None:
        trace = result.judge_trace
        cost = summarize_call(
            trace.model if trace else None,
            _judge_usage(trace),
        ) if trace else None
        judge = ShowcaseJudge(
            result=result.thread_check.result,
            reason=result.thread_check.reason,
            evidence=result.thread_check.evidence,
            model=trace.model if trace else None,
            reasoning_effort=trace.reasoning_effort if trace else None,
            latency_ms=trace.latency_ms if trace else None,
            input_tokens=trace.input_tokens if trace else None,
            cached_input_tokens=trace.cached_input_tokens if trace else None,
            cache_write_tokens=trace.cache_write_tokens if trace else None,
            output_tokens=trace.output_tokens if trace else None,
            reasoning_tokens=trace.reasoning_tokens if trace else None,
            total_tokens=trace.total_tokens if trace else None,
            cost=cost.cost if cost else None,
            reasoning_summaries=trace.reasoning_summaries if trace else [],
            criteria=[
                criterion.criteria.strip() for criterion in result.thread_expectation.criteria
            ],
        )
    return ShowcaseScenario(
        id=result.id,
        title=result.title,
        question=result.question,
        category=result.category,
        goal=result.goal,
        status=result.status,
        judge=judge,
        turns=[_turn(turn) for turn in result.turns],
    )


def _turn(turn: GoldenTurnResult) -> ShowcaseTurn:
    record = turn.record if isinstance(turn.record, dict) else {}
    return ShowcaseTurn(
        id=turn.id,
        action=_action_label(turn.action),
        status=_turn_status(turn),
        golden=ShowcaseGolden(
            criteria=turn.golden.criteria.strip(),
            calls=[_golden_call(call) for call in turn.golden.calls],
        ),
        story=_story(record),
        checks=[_check(check) for check in turn.checks],
        traces=[_trace(trace) for trace in _dict_list(record.get("agent_traces"))],
    )


def _golden_call(call: GoldenAgentResult) -> ShowcaseGoldenCall:
    return ShowcaseGoldenCall(
        agent=call.agent,
        output_type=call.output_type,
        output=_public_output(call.output_type, call.output),
    )


def _story(record: dict[str, Any]) -> ShowcaseStory:
    mechanical = record.get("mechanical_result")
    exchange = record.get("exchange")
    menu = record.get("follow_up_menu")
    narration = record.get("event_narration")
    commits = record.get("agent_commits")
    return ShowcaseStory(
        engine_result=_engine_result(mechanical),
        relationship_changes=_relationship_changes(mechanical),
        dialogue=_dialogue(exchange),
        narration=str(narration.get("prose"))
        if isinstance(narration, dict) and narration.get("prose")
        else None,
        choices=_choices(menu),
        events=_events(record.get("ceremony_events")),
        memories=_memories(commits),
        resort_changes=_resort_changes(commits),
    )


def _engine_result(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    bits = [f"Success: {'yes' if value.get('success') else 'no'}"]
    if value.get("success_chance") is not None:
        bits.append(f"Chance: {value['success_chance']}")
    if value.get("roll") is not None:
        bits.append(f"Roll: {value['roll']}")
    tags = value.get("tags")
    if isinstance(tags, list) and tags:
        bits.append("Tags: " + ", ".join(str(tag) for tag in tags))
    return " | ".join(bits)


def _relationship_changes(value: object) -> list[str]:
    if not isinstance(value, dict) or not isinstance(value.get("relationship_deltas"), dict):
        return []
    changes = []
    for target, delta in value["relationship_deltas"].items():
        if not isinstance(delta, dict):
            continue
        changed = [
            f"{key} {amount:+d}"
            for key, amount in delta.items()
            if isinstance(amount, int) and amount
        ]
        if changed:
            changes.append(f"{target}: {', '.join(changed)}")
    return changes


def _dialogue(value: object) -> ShowcaseDialogue | None:
    if not isinstance(value, dict):
        return None
    return ShowcaseDialogue(
        player=str(value.get("player_dialogue", "")),
        npc=str(value.get("npc_dialogue", "")),
        tone=str(value["npc_tone"]) if value.get("npc_tone") else None,
        mood_after=str(value["npc_mood_after"]) if value.get("npc_mood_after") else None,
    )


def _choices(value: object) -> list[ShowcaseChoice]:
    if not isinstance(value, dict):
        return []
    return [
        ShowcaseChoice(
            label=str(option.get("label", "")),
            category=str(option.get("category", "")),
            risk=str(option.get("risk", "")),
        )
        for option in _dict_list(value.get("options"))
    ]


def _events(value: object) -> list[str]:
    return [
        f"{event.get('kind', 'event')}: {event.get('message', '')}" for event in _dict_list(value)
    ]


def _memories(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    memories = []
    for batch in _dict_list(value.get("curator_batches")):
        if batch.get("summary"):
            memories.append(f"Summary: {batch['summary']}")
        for memory in _dict_list(batch.get("memories")):
            memories.append(
                f"{memory.get('holder_id', 'holder')} -> {memory.get('subject_id', 'subject')}: "
                f"{memory.get('content', '')}"
            )
    return memories


def _resort_changes(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    update = value.get("resort_update")
    parts = []
    if isinstance(update, dict) and update.get("conversation_starts"):
        parts.append(f"{len(update['conversation_starts'])} background conversation(s) started")
    if isinstance(update, dict) and update.get("npc_movements"):
        parts.append(f"{len(update['npc_movements'])} NPC movement(s)")
    if isinstance(value.get("background_dialogues"), list) and value["background_dialogues"]:
        parts.append(f"{len(value['background_dialogues'])} background dialogue beat(s)")
    return "; ".join(parts) or None


def _trace(value: dict[str, Any]) -> ShowcaseTrace:
    usage = value.get("usage")
    usage_payload = usage if isinstance(usage, dict) else {}
    cost = summarize_call(str(value.get("model", "")), usage_payload)
    return ShowcaseTrace(
        agent=str(value.get("agent_name", "agent")),
        model=str(value.get("model", "unknown")),
        reasoning_effort=str(value.get("reasoning_effort", "unknown")),
        output_type=str(value["output_type"]) if value.get("output_type") else None,
        latency_ms=value.get("latency_ms") if isinstance(value.get("latency_ms"), int) else None,
        input_tokens=usage.get("input_tokens")
        if isinstance(usage, dict) and isinstance(usage.get("input_tokens"), int)
        else None,
        cached_input_tokens=usage.get("cached_input_tokens")
        if isinstance(usage, dict) and isinstance(usage.get("cached_input_tokens"), int)
        else None,
        cache_write_tokens=usage.get("cache_write_tokens")
        if isinstance(usage, dict) and isinstance(usage.get("cache_write_tokens"), int)
        else None,
        output_tokens=usage.get("output_tokens")
        if isinstance(usage, dict) and isinstance(usage.get("output_tokens"), int)
        else None,
        reasoning_tokens=usage.get("reasoning_tokens")
        if isinstance(usage, dict) and isinstance(usage.get("reasoning_tokens"), int)
        else None,
        total_tokens=usage.get("total_tokens")
        if isinstance(usage, dict) and isinstance(usage.get("total_tokens"), int)
        else None,
        cost=cost.cost,
        output=_public_trace_output(value),
        reasoning_summaries=_reasoning_summaries(value.get("reasoning_summaries")),
        attempt=value.get("attempt") if isinstance(value.get("attempt"), int) else 1,
    )


_PUBLIC_OUTPUT_FIELDS: dict[str, tuple[str, ...]] = {
    "Exchange": ("player_dialogue", "npc_dialogue", "npc_tone", "npc_mood_after"),
    "ContextualBespoke": ("options", "npc_will_leave", "npc_exit_line"),
    "FollowUpMenu": ("options", "npc_will_leave", "npc_exit_line"),
    "MemoryBatch": ("kind", "memories", "summary", "gossip_seeds"),
    "EventNarration": ("prose",),
    "ResortUpdate": (
        "npc_movements",
        "conversation_starts",
        "conversation_continues",
        "conversation_ends",
        "npc_interruptions",
        "npc_summoned_elsewhere",
    ),
    "BackgroundExchange": ("speaker_a_line", "speaker_b_line", "tone"),
}


def _public_trace_output(value: dict[str, Any]) -> object:
    output = value.get("output")
    output_type = value.get("output_type")
    if not isinstance(output, dict):
        return None
    return _public_output(str(output_type), output)


def _public_output(output_type: str, output: dict[str, Any]) -> dict[str, Any]:
    fields = _PUBLIC_OUTPUT_FIELDS.get(str(output_type))
    if fields is None:
        return {}
    return {field: output[field] for field in fields if field in output}


def _reasoning_summaries(value: object) -> list[str]:
    summaries = []
    for item in _dict_list(value):
        texts = item.get("texts")
        if isinstance(texts, list):
            summaries.extend(str(text) for text in texts if isinstance(text, str) and text.strip())
    return summaries


def _judge_usage(trace: object) -> dict[str, object]:
    if trace is None:
        return {}
    return {
        key: value
        for key in (
            "input_tokens",
            "cached_input_tokens",
            "cache_write_tokens",
            "output_tokens",
            "reasoning_tokens",
            "total_tokens",
        )
        if (value := getattr(trace, key, None)) is not None
    }


def _check(check: GoldenCheckResult) -> ShowcaseCheck:
    return ShowcaseCheck(
        id=check.id,
        kind=check.kind,
        result=check.result,
        reason=check.reason,
        evidence=check.evidence,
    )


def _turn_status(turn: GoldenTurnResult) -> CheckResultValue:
    results = [check.result for check in turn.checks]
    if "fail" in results:
        return "fail"
    if "cannot_determine" in results:
        return "cannot_determine"
    return "pass"


def _action_label(action: dict[str, Any]) -> str:
    parts = [str(action.get("kind", "action"))]
    if action.get("target_id"):
        parts.append(f"target {action['target_id']}")
    if action.get("intent_id"):
        parts.append(f"intent {action['intent_id']}")
    return " | ".join(parts)


def _dict_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
