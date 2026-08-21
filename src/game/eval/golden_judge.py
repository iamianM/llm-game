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
    GoldenCheckResult,
    GoldenEvalScenario,
    JudgeTrace,
    ThreadCheckSpec,
)


class JudgeReport(BaseModel):
    """The single holistic judge verdict for one complete scenario."""

    model_config = ConfigDict(extra="forbid")

    result: Literal["pass", "fail", "cannot_determine"]
    reason: str
    evidence: str | None = None


def run_thread_check(
    *,
    scenario: GoldenEvalScenario,
    records: list[dict[str, object]],
    deterministic_checks: list[list[GoldenCheckResult]],
    prompt_out: Path,
) -> tuple[GoldenCheckResult, JudgeTrace]:
    """Return one holistic verdict for one complete scenario thread."""
    load_dotenv_local()
    prompt = build_thread_judge_prompt(
        scenario=scenario,
        records=records,
        deterministic_checks=deterministic_checks,
    )
    prompt_out.parent.mkdir(parents=True, exist_ok=True)
    prompt_out.write_text(prompt, encoding="utf-8")
    client = build_game_client()
    started = perf_counter()
    response, attempts, retry_errors = _request_judge_report(client, prompt)
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


def _request_judge_report(client: Any, prompt: str) -> tuple[Any, int, list[str]]:
    """Retry only transient judge failures without rerunning gameplay agents."""
    retry_errors: list[str] = []
    for attempt in range(1, _JUDGE_ATTEMPTS + 1):
        try:
            response = client.responses.parse(
                model=JUDGE_PROFILE.model,
                instructions=JUDGE_INSTRUCTIONS,
                input=prompt,
                text_format=JudgeReport,
                **reasoning_request_kwargs(effort=JUDGE_PROFILE.reasoning_effort),
            )
            return response, attempt, retry_errors
        except _RETRYABLE_JUDGE_ERRORS as exc:
            retry_errors.append(f"{type(exc).__name__}: {exc}")
            if attempt == _JUDGE_ATTEMPTS:
                raise
            sleep(0.25 * attempt)
    raise AssertionError("unreachable judge retry state")


JUDGE_INSTRUCTIONS = (
    "Review the complete dating-sim scenario as one thread. Judge continuity, voice, "
    "specificity, and outcome faithfulness across turns rather than grading isolated lines. "
    "Each golden contains reviewed agent results in the same shape as the actual calls plus semantic "
    "criteria. Compare natural language by meaning, voice, and continuity rather than exact wording. "
    "Compare agent identity, output type, and structured contract fields exactly. Engine fields inside each actual "
    "record are deterministic ground truth for mechanics, participants, outcomes, and state. "
    "Return pass for a reasonable semantic match, fail for a material mismatch visible in "
    "the evidence, and cannot_determine only when the thread lacks the needed evidence. "
    "Do not infer hidden state. Apply every supplied criterion, then return exactly one "
    "holistic verdict for the scenario's thread_check."
)


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
    """Keep model outputs but exclude duplicated inputs and judge-biasing reasoning."""
    if not isinstance(raw, list):
        return []
    keys = ("agent_name", "output_type", "output", "validation_error", "degraded")
    return [{key: item.get(key) for key in keys} for item in raw if isinstance(item, dict)]


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
