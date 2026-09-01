"""Optional thread-level LLM judge for golden eval scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter, sleep
from typing import Any, Literal

from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError
from pydantic import BaseModel, ConfigDict

from src.game.agents.heartbreaker_voice import load_dotenv_local
from src.game.agents.runtime import (
    JUDGE_PROFILE,
    build_game_client,
    extract_reasoning_summaries,
    reasoning_request_kwargs,
)
from src.game.eval.golden_models import (
    ExecutionModel,
    GoldenCheckResult,
    GoldenEvalScenario,
    JudgeCriterionFinding,
    JudgeTrace,
    ThreadCheckSpec,
)


class JudgeReport(BaseModel):
    """The single holistic judge verdict for one complete scenario."""

    model_config = ConfigDict(extra="forbid")

    result: Literal["pass", "fail", "cannot_determine"]
    reason: str
    evidence: str | None = None
    criterion_findings: list[JudgeCriterionFinding]


def run_thread_check(
    *,
    scenario: GoldenEvalScenario,
    records: list[dict[str, object]],
    deterministic_checks: list[list[GoldenCheckResult]],
    prompt_out: Path,
    execution_model: ExecutionModel = "isolated_golden_replay",
) -> tuple[GoldenCheckResult, JudgeTrace]:
    """Return one holistic verdict for one complete scenario thread."""
    load_dotenv_local()
    prompt = build_thread_judge_prompt(
        scenario=scenario,
        records=records,
        deterministic_checks=deterministic_checks,
        execution_model=execution_model,
    )
    prompt_out.parent.mkdir(parents=True, exist_ok=True)
    prompt_out.write_text(prompt, encoding="utf-8")
    client = build_game_client()
    started = perf_counter()
    response, attempts, retry_errors = _request_judge_report(
        client,
        prompt,
        scenario.thread_check,
        execution_model,
    )
    report = response.output_parsed
    if report is None:
        result = GoldenCheckResult(
            id=scenario.thread_check.id,
            kind="judge",
            result="cannot_determine",
            reason="judge returned no parsed report",
            severity=scenario.thread_check.severity,
        )
    else:
        result = GoldenCheckResult(
            id=scenario.thread_check.id,
            kind="judge",
            result=report.result,
            reason=report.reason,
            evidence=report.evidence,
            severity=scenario.thread_check.severity,
            criterion_findings=report.criterion_findings,
        )
    return result, _judge_trace(
        response,
        prompt_out,
        started,
        attempts=attempts,
        retry_errors=retry_errors,
    )


def build_thread_judge_prompt(
    *,
    scenario: GoldenEvalScenario,
    records: list[dict[str, object]],
    deterministic_checks: list[list[GoldenCheckResult]] | None = None,
    execution_model: ExecutionModel = "isolated_golden_replay",
) -> str:
    """Build the complete-thread evidence payload for one judge call."""
    turns = []
    for index, turn_spec in enumerate(scenario.turns):
        record: dict[str, object] = (
            records[index] if index < len(records) else {"error": "turn did not complete"}
        )
        turns.append(
            {
                "turn_id": turn_spec.id,
                "input_source": {
                    "fresh_scenario_state": True,
                    "reviewed_prior_turn_ids": [prior.id for prior in scenario.turns[:index]]
                    if execution_model == "isolated_golden_replay"
                    else [],
                    "actual_prior_turn_ids": [prior.id for prior in scenario.turns[:index]]
                    if execution_model == "causal_rollout"
                    else [],
                },
                "action": turn_spec.action.model_dump(mode="json"),
                "golden": turn_spec.golden.model_dump(mode="json"),
                "actual": _actual_payload(record),
                "deterministic_checks": [
                    check.model_dump(mode="json")
                    for check in (
                        deterministic_checks[index]
                        if deterministic_checks is not None and index < len(deterministic_checks)
                        else []
                    )
                ],
            }
        )
    payload = {
        "scenario_title": scenario.title,
        "scenario_goal": scenario.goal,
        "scenario_context": scenario.judge_context,
        "execution_model": execution_model,
        "thread": turns,
        "thread_check": _thread_check_payload(scenario.thread_check),
    }
    return json.dumps(payload, indent=2, sort_keys=True)


_RETRYABLE_JUDGE_ERRORS = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
)
_JUDGE_ATTEMPTS = 3


def _request_judge_report(
    client: Any,
    prompt: str,
    check: ThreadCheckSpec,
    execution_model: ExecutionModel,
) -> tuple[Any, int, list[str]]:
    """Retry transient or structured-output failures without rerunning gameplay."""
    retry_errors: list[str] = []
    request_input = prompt
    for attempt in range(1, _JUDGE_ATTEMPTS + 1):
        try:
            response = client.responses.parse(
                model=JUDGE_PROFILE.model,
                instructions=_judge_instructions(execution_model),
                input=request_input,
                text_format=JudgeReport,
                **reasoning_request_kwargs(effort=JUDGE_PROFILE.reasoning_effort),
            )
            report = response.output_parsed
            if report is not None:
                try:
                    _validate_judge_report(report, check, json.loads(prompt))
                except ValueError as exc:
                    retry_errors.append(f"JudgeValidationError: {exc}")
                    if attempt == _JUDGE_ATTEMPTS:
                        raise
                    request_input = (
                        f"{prompt}\n\nYour previous report failed schema validation: {exc}. "
                        "Return a corrected report using only the thread_check criteria."
                    )
                    continue
            return response, attempt, retry_errors
        except _RETRYABLE_JUDGE_ERRORS as exc:
            retry_errors.append(f"{type(exc).__name__}: {exc}")
            if attempt == _JUDGE_ATTEMPTS:
                raise
            sleep(0.25 * attempt)
    raise AssertionError("unreachable judge retry state")


_COMMON_JUDGE_INSTRUCTIONS = (
    "Inspect every supplied criterion against the actions, deterministic engine records, reviewed "
    "outputs, and actual model calls. Engine fields are ground truth for participants, mechanics, "
    "outcomes, and state. Compare reviewed prose by meaning, voice, continuity, and specificity, not "
    "exact wording. Compare agent identity, output type, participant ids, and other structured contract "
    "fields exactly when the rubric requires that match or one actual call consumes another. Treat "
    "reviewed natural-language outputs as semantic references rather than exact string snapshots. For "
    "each item under thread_check.criteria, return exactly one criterion_finding in the same order, using "
    "the exact criterion_id. Do not emit findings for turn ids. Give each finding a verdict and a concrete "
    "reason. Set the report-level evidence field to null. For each failed or indeterminate finding, copy "
    "one short exact excerpt from that turn's reviewed target, actual output, engine record, or deterministic "
    "check into the finding evidence field. Do not paraphrase, correct, label, or combine excerpts. Pass "
    "findings may leave evidence null. Memory holder_id defines whose first-person memory it is: in an "
    "NPC-held memory, I/my refers to that NPC and the phrase 'the player' correctly names the other "
    "participant. When a criterion covers dialogue quality, reject therapy framing, trailer-ready speeches, "
    "interchangeable wit, instant confessions, and repeated stock phrasing even when the schema is valid. "
    "Try to falsify the criterion; do not award a pass because the deterministic checks passed. Use "
    "cannot_determine only when required evidence is absent, and do not infer hidden state. The overall "
    "result must be fail if any criterion fails, cannot_determine if none fail and any cannot be determined, "
    "and pass only if every criterion passes."
)


def _judge_instructions(execution_model: ExecutionModel) -> str:
    if execution_model == "causal_rollout":
        return (
            "Audit the complete dating-sim scenario as one causal rollout. The first actual turn ran from "
            "fresh scenario state; every later actual turn continued from all earlier actual outputs. Judge "
            "continuity, memory, repetition, and state across the actual sequence. The reviewed calls remain "
            "turn-level semantic references, not replayed inputs. "
            + _COMMON_JUDGE_INSTRUCTIONS
        )
    return (
        "Audit the complete dating-sim scenario as isolated golden-replay turns. Every actual turn ran "
    "from fresh scenario state after the runner replayed all earlier reviewed outputs. Earlier actual "
    "outputs never become input to a later turn. For turn N, judge the actual calls against that turn's "
    "reviewed calls and the reviewed calls from turns 1 through N-1. Do not demand continuity with an "
    "earlier actual output. Calls inside one target turn still run in order. A later call in that target "
    "may use an earlier actual call from the same target. For example, a closing curator sees the reviewed "
    "prior conversation plus the actual closing exchange. Treat both as valid evidence. Inspect every "
        "supplied criterion against the reviewed prefix, not against earlier actual turns. "
        + _COMMON_JUDGE_INSTRUCTIONS
    )


def _validate_judge_report(
    report: JudgeReport,
    check: ThreadCheckSpec,
    evidence_payload: dict[str, object],
) -> None:
    expected_ids = [criterion.id for criterion in check.criteria]
    actual_ids = [finding.criterion_id for finding in report.criterion_findings]
    if actual_ids != expected_ids:
        raise ValueError(
            "judge criterion findings must match authored criterion order: "
            f"expected {expected_ids!r}, got {actual_ids!r}"
        )
    finding_results = [finding.result for finding in report.criterion_findings]
    expected_result: Literal["pass", "fail", "cannot_determine"]
    if "fail" in finding_results:
        expected_result = "fail"
    elif "cannot_determine" in finding_results:
        expected_result = "cannot_determine"
    else:
        expected_result = "pass"
    if report.result != expected_result:
        raise ValueError(
            f"judge overall result must be {expected_result!r} from criterion findings, "
            f"got {report.result!r}"
        )
    if report.evidence is not None:
        raise ValueError("judge report-level evidence must be null; cite each finding instead")
    evidence_texts = _thread_evidence_texts(evidence_payload)
    for finding in report.criterion_findings:
        if finding.result != "pass" and not finding.evidence:
            raise ValueError(
                f"judge finding {finding.criterion_id!r} requires one exact evidence excerpt"
            )
        if finding.evidence and not any(
            finding.evidence in text for text in evidence_texts
        ):
            raise ValueError(
                f"judge finding {finding.criterion_id!r} cited text absent from thread evidence: "
                f"{finding.evidence!r}"
            )


def _thread_evidence_texts(payload: dict[str, object]) -> list[str]:
    """Return strings from reviewed targets, actual records, and deterministic checks."""
    texts: list[str] = []

    def collect(value: object) -> None:
        if isinstance(value, str):
            texts.append(value)
        elif isinstance(value, dict):
            texts.append(json.dumps(value, sort_keys=True))
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            texts.append(json.dumps(value, sort_keys=True))
            for item in value:
                collect(item)

    for turn in payload.get("thread", []):
        if not isinstance(turn, dict):
            continue
        collect(turn.get("golden"))
        collect(turn.get("actual"))
        collect(turn.get("deterministic_checks"))
    return texts


def _thread_check_payload(check: ThreadCheckSpec) -> dict[str, object]:
    return {
        "id": check.id,
        "severity": check.severity,
        "criteria": [criterion.model_dump(mode="json") for criterion in check.criteria],
    }


def _actual_payload(record: dict[str, object]) -> dict[str, object]:
    keys = (
        "exchange",
        "follow_up_menu",
        "event_narration",
        "agent_commits",
        "mechanical_result",
        "ceremony_events",
        "challenge",
        "producer_text",
        "pending_gather",
        "audience_snapshot",
        "revealed_preferences",
        "daily_recaps",
        "visible_state",
        "resort_snapshot",
        "location",
        "day",
        "phase",
        "error",
    )
    payload = {key: record.get(key) for key in keys}
    payload["agent_traces"] = _judge_agent_traces(record.get("agent_traces"))
    return payload


def _judge_agent_traces(raw: object) -> list[dict[str, object]]:
    """Give the judge accepted outputs, not rejected retry attempts."""
    if not isinstance(raw, list):
        return []
    keys = ("agent_name", "output_type", "output", "degraded")
    return [
        {key: item.get(key) for key in keys}
        for item in raw
        if isinstance(item, dict)
        and item.get("output") is not None
        and not item.get("validation_error")
        and not item.get("generation_error")
    ]


def _judge_trace(
    response: object,
    prompt_out: Path,
    started: float,
    *,
    attempts: int,
    retry_errors: list[str],
) -> JudgeTrace:
    usage = getattr(response, "usage", None)
    summaries = [text for item in extract_reasoning_summaries(response) for text in item.texts]
    return JudgeTrace(
        model=JUDGE_PROFILE.model,
        reasoning_effort=JUDGE_PROFILE.reasoning_effort,
        prompt_path=prompt_out.as_posix(),
        latency_ms=round((perf_counter() - started) * 1000),
        response_id=_string_attr(response, "id"),
        input_tokens=_int_attr(usage, "input_tokens"),
        cached_input_tokens=_nested_int_attr(usage, "input_tokens_details", "cached_tokens"),
        cache_write_tokens=_nested_int_attr(
            usage, "input_tokens_details", "cache_write_tokens"
        ),
        output_tokens=_int_attr(usage, "output_tokens"),
        reasoning_tokens=_nested_int_attr(
            usage, "output_tokens_details", "reasoning_tokens"
        ),
        total_tokens=_int_attr(usage, "total_tokens"),
        attempts=attempts,
        retry_errors=retry_errors,
        reasoning_summaries=summaries,
    )


def _string_attr(value: object, key: str) -> str | None:
    item = getattr(value, key, None)
    return str(item) if item is not None else None


def _int_attr(value: object, key: str) -> int | None:
    item = getattr(value, key, None)
    return int(item) if isinstance(item, int) else None


def _nested_int_attr(value: object, parent: str, key: str) -> int | None:
    return _int_attr(getattr(value, parent, None), key)
