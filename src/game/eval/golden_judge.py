"""Optional LLM judge for golden eval scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from src.game.agents.heartbreaker_voice import load_dotenv_local
from src.game.agents.runtime import GAME_AGENT_MODEL, reasoning_request_kwargs
from src.game.eval.golden_models import GoldenCheckResult, GoldenTurnSpec, JudgeCheckSpec


class JudgeItem(BaseModel):
    """One judge result."""

    model_config = ConfigDict(extra="forbid")

    id: str
    result: Literal["pass", "fail", "cannot_determine"]
    reason: str
    evidence: str | None = None


class JudgeReport(BaseModel):
    """Structured judge response."""

    model_config = ConfigDict(extra="forbid")

    results: list[JudgeItem] = Field(default_factory=list)


def run_judge_checks(
    *,
    scenario_title: str,
    scenario_goal: str,
    scenario_context: list[str],
    turn_spec: GoldenTurnSpec,
    record: dict[str, object],
    prior_records: list[dict[str, object]] | None = None,
    prompt_out: Path,
    model: str = GAME_AGENT_MODEL,
) -> list[GoldenCheckResult]:
    """Run judge checks for one turn and persist the prompt."""
    if not turn_spec.judge_checks:
        return []
    load_dotenv_local()
    prompt = build_judge_prompt(
        scenario_title=scenario_title,
        scenario_goal=scenario_goal,
        scenario_context=scenario_context,
        turn_spec=turn_spec,
        record=record,
        prior_records=prior_records or [],
    )
    prompt_out.parent.mkdir(parents=True, exist_ok=True)
    prompt_out.write_text(prompt, encoding="utf-8")
    client = OpenAI()
    required_ids = {check.id for check in turn_spec.judge_checks}
    last_report: JudgeReport | None = None
    last_reason = "judge returned no parsed report"
    for attempt in range(2):
        judge_input = prompt if attempt == 0 else _retry_prompt(prompt, sorted(required_ids))
        response = client.responses.parse(
            model=model,
            instructions=JUDGE_INSTRUCTIONS,
            input=judge_input,
            text_format=JudgeReport,
            **reasoning_request_kwargs(),
        )
        report = response.output_parsed
        if report is None:
            continue
        last_report = report
        returned_ids = {item.id for item in report.results}
        missing = required_ids - returned_ids
        if not missing:
            by_id = {item.id: item for item in report.results}
            return [_coerce_judge_result(check, by_id.get(check.id), turn_spec.id) for check in turn_spec.judge_checks]
        last_reason = f"judge omitted exact check id(s): {sorted(missing)}"
    by_id = {item.id: item for item in last_report.results} if last_report is not None else {}
    results = [_coerce_judge_result(check, by_id.get(check.id), turn_spec.id) for check in turn_spec.judge_checks]
    return [
        result.model_copy(update={"reason": last_reason})
        if result.result == "cannot_determine" and result.reason.startswith("judge ")
        else result
        for result in results
    ]


def build_judge_prompt(
    *,
    scenario_title: str,
    scenario_goal: str,
    scenario_context: list[str],
    turn_spec: GoldenTurnSpec,
    record: dict[str, object],
    prior_records: list[dict[str, object]],
) -> str:
    """Build a self-contained judge prompt for one turn."""
    checks = [_judge_check_payload(check) for check in turn_spec.judge_checks]
    payload = {
        "scenario_title": scenario_title,
        "scenario_goal": scenario_goal,
        "scenario_context": scenario_context,
        "turn_id": turn_spec.id,
        "action": turn_spec.action.model_dump(mode="json"),
        "golden": turn_spec.golden,
        "prior_turns": [_actual_payload(item) for item in prior_records],
        "actual": _actual_payload(record),
        "checks": checks,
    }
    return json.dumps(payload, indent=2, sort_keys=True)


JUDGE_INSTRUCTIONS = (
    "You are judging generated dating-sim agent output against an authored golden. "
    "Use the golden as expected INTENT and shape, not as a script. "
    "CRITICAL: The fields under `actual` named `ceremony_events`, `challenge`, "
    "`mechanical_result`, `producer_text`, `pending_gather`, `audience_snapshot`, "
    "`revealed_preferences`, `daily_recaps`, `resort_snapshot`, `location`, "
    "`day`, and `phase` are the engine's deterministic ground truth. When a "
    "judge criterion asks whether the narrator 'matches the recorded outcome' "
    "(winner, couples, eliminated heartbreaker, classification, BPMs, proposal "
    "result, etc.), compare ONLY against those engine fields — never against "
    "names that appear in the golden's 'Imagine:' illustrative example. The "
    "illustrative example shows the desired shape and tone of prose, not which "
    "specific heartbreakers should win or lose. If the engine recorded `player and "
    "chloe win` and the narration says the same, that passes a "
    "final_outcome_faithful check even if the golden's Imagine: paragraph "
    "named different heartbreakers. "
    "Return pass when the actual output is a reasonable semantic match to the "
    "criterion AND consistent with engine ground truth. "
    "Return fail only for a material mismatch grounded in the visible actual output. "
    "Return cannot_determine when the artifact lacks enough evidence. "
    "For memory or close-turn checks, compare curator memories against prior_turns "
    "player exchanges, not against unrelated background_dialogues. "
    "Do not invent hidden game state."
)


def _judge_check_payload(check: JudgeCheckSpec) -> dict[str, object]:
    return {
        "id": check.id,
        "criteria": check.criteria,
        "pass_examples": check.pass_examples,
        "fail_examples": check.fail_examples,
    }


def _retry_prompt(prompt: str, required_ids: list[str]) -> str:
    ids = ", ".join(required_ids)
    return (
        f"{prompt}\n\n"
        "The previous judge response omitted at least one required check id. "
        f"Return exactly one result for each of these ids, spelling each id exactly: {ids}."
    )


def _actual_payload(record: dict[str, object]) -> dict[str, object]:
    return {
        "exchange": record.get("exchange"),
        "follow_up_menu": record.get("follow_up_menu"),
        "event_narration": record.get("event_narration"),
        "agent_commits": record.get("agent_commits"),
        "agent_traces": record.get("agent_traces"),
        "mechanical_result": record.get("mechanical_result"),
        # Deterministic engine outputs. The judge MUST use these as ground truth
        # for "did the narrator stay faithful to the recorded outcome" checks.
        # When the golden's prose includes an illustrative "Imagine:" example,
        # ignore those names — these fields are the engine's authoritative record.
        "ceremony_events": record.get("ceremony_events"),
        "challenge": record.get("challenge"),
        "producer_text": record.get("producer_text"),
        "pending_gather": record.get("pending_gather"),
        "audience_snapshot": record.get("audience_snapshot"),
        "revealed_preferences": record.get("revealed_preferences"),
        "daily_recaps": record.get("daily_recaps"),
        "visible_state": record.get("visible_state"),
        "resort_snapshot": record.get("resort_snapshot"),
        "location": record.get("location"),
        "day": record.get("day"),
        "phase": record.get("phase"),
    }


def _coerce_judge_result(
    check: JudgeCheckSpec,
    item: JudgeItem | None,
    turn_id: str,
) -> GoldenCheckResult:
    if item is None:
        return GoldenCheckResult(
            id=check.id,
            kind="judge",
            result="cannot_determine",
            reason="judge omitted this check id",
            turn_id=turn_id,
        )
    return GoldenCheckResult(
        id=check.id,
        kind="judge",
        result=item.result,
        reason=item.reason,
        evidence=item.evidence,
        turn_id=turn_id,
    )
