from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError

from src.game.eval import golden_judge
from src.game.eval.golden_judge import JudgeReport, build_thread_judge_prompt, run_thread_check
from src.game.eval.golden_models import GoldenCheckResult, JudgeCriterionFinding
from src.game.eval.golden_runner import load_golden_scenario


def test_thread_judge_prompt_contains_complete_scenario_once() -> None:
    scenario = load_golden_scenario(Path("evals/llm/scenarios/conversation-continuity-exit.yaml"))
    records = [{"exchange": {"npc_dialogue": turn.id}} for turn in scenario.turns]

    checks = [
        [
            GoldenCheckResult(
                id="conversation_active",
                kind="deterministic",
                result="pass",
                reason="conversation remains active",
            )
        ]
        for _turn in scenario.turns
    ]
    payload = json.loads(
        build_thread_judge_prompt(
            scenario=scenario,
            records=records,
            deterministic_checks=checks,
        )
    )

    assert [turn["turn_id"] for turn in payload["thread"]] == [turn.id for turn in scenario.turns]
    assert payload["thread_check"]["id"] == "thread_acceptance"
    assert {criterion["id"] for criterion in payload["thread_check"]["criteria"]} == {
        "conversation_arc_continuity",
        "chloe_voice_and_memory",
    }
    assert all("actual" in turn and "golden" in turn for turn in payload["thread"])
    assert payload["thread"][0]["golden"]["calls"][0]["output_type"] == "Exchange"
    assert payload["thread"][1]["golden"]["calls"][0]["output"] is None
    assert payload["thread"][1]["golden"]["calls"][0]["criteria"]
    assert all(
        turn["deterministic_checks"][0]["id"] == "conversation_active" for turn in payload["thread"]
    )


def test_thread_judge_prompt_excludes_rejected_agent_attempts() -> None:
    traces = golden_judge._judge_agent_traces(
        [
            {
                "agent_name": "event_narrator",
                "output_type": "EventNarration",
                "output": {"prose": "Rejected output"},
                "validation_error": "mentioned an off-scene participant",
                "attempt": 1,
            },
            {
                "agent_name": "event_narrator",
                "output_type": "EventNarration",
                "output": {"prose": "Accepted output"},
                "validation_error": None,
                "attempt": 2,
            },
        ]
    )

    assert traces == [
        {
            "agent_name": "event_narrator",
            "output_type": "EventNarration",
            "output": {"prose": "Accepted output"},
            "degraded": None,
        }
    ]


def test_thread_judge_retries_transient_connection_failure(monkeypatch, tmp_path: Path) -> None:
    scenario = load_golden_scenario(Path("evals/llm/scenarios/opening-ceremony.yaml"))
    response = SimpleNamespace(
        output_parsed=JudgeReport(
            result="pass",
            reason="faithful",
            criterion_findings=[
                JudgeCriterionFinding(
                    criterion_id="first_spark_story_faithful",
                    result="pass",
                    reason="The narrated pairing matches the engine record.",
                    evidence=None,
                )
            ],
        ),
        usage=None,
        output=[],
        id="response-1",
    )

    class FakeResponses:
        def __init__(self) -> None:
            self.calls = 0

        def parse(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise APIConnectionError(
                    request=httpx.Request("POST", "https://api.openai.com/v1/responses")
                )
            return response

    responses = FakeResponses()
    monkeypatch.setattr(
        golden_judge, "build_game_client", lambda: SimpleNamespace(responses=responses)
    )
    monkeypatch.setattr(golden_judge, "sleep", lambda _seconds: None)

    result, trace = run_thread_check(
        scenario=scenario,
        records=[{}],
        deterministic_checks=[[]],
        prompt_out=tmp_path / "judge.json",
    )

    assert result.result == "pass"
    assert result.criterion_findings[0].criterion_id == "first_spark_story_faithful"
    assert trace.attempts == 2
    assert trace.retry_errors and trace.retry_errors[0].startswith("APIConnectionError:")


def test_thread_judge_retries_wrong_criterion_ids(monkeypatch, tmp_path: Path) -> None:
    scenario = load_golden_scenario(Path("evals/llm/scenarios/opening-ceremony.yaml"))
    invalid = JudgeReport(
        result="pass",
        reason="used the turn id instead of the criterion id",
        criterion_findings=[
            JudgeCriterionFinding(
                criterion_id="couple-with-chloe",
                result="pass",
                reason="wrong identifier",
            )
        ],
    )
    valid = JudgeReport(
        result="pass",
        reason="faithful",
        criterion_findings=[
            JudgeCriterionFinding(
                criterion_id="first_spark_story_faithful",
                result="pass",
                reason="The narrated pairing matches the engine record.",
            )
        ],
    )

    class FakeResponses:
        def __init__(self) -> None:
            self.calls = 0

        def parse(self, **_kwargs):
            self.calls += 1
            report = invalid if self.calls == 1 else valid
            return SimpleNamespace(
                output_parsed=report,
                usage=None,
                output=[],
                id=f"response-{self.calls}",
            )

    responses = FakeResponses()
    monkeypatch.setattr(
        golden_judge, "build_game_client", lambda: SimpleNamespace(responses=responses)
    )

    result, trace = run_thread_check(
        scenario=scenario,
        records=[{}],
        deterministic_checks=[[]],
        prompt_out=tmp_path / "judge.json",
    )

    assert result.result == "pass"
    assert trace.attempts == 2
    assert trace.retry_errors == [
        "JudgeValidationError: judge criterion findings must match authored criterion order: "
        "expected ['first_spark_story_faithful'], got ['couple-with-chloe']"
    ]


def test_judge_rejects_hallucinated_failure_evidence() -> None:
    scenario = load_golden_scenario(
        Path("evals/llm/scenarios/conversation-continuity-exit.yaml")
    )
    findings = [
        JudgeCriterionFinding(
            criterion_id=criterion.id,
            result="fail" if index == 0 else "pass",
            reason="failed" if index == 0 else "passed",
            evidence="Chloe said a sentence that does not exist" if index == 0 else None,
        )
        for index, criterion in enumerate(scenario.thread_check.criteria)
    ]
    report = JudgeReport(result="fail", reason="one criterion failed", criterion_findings=findings)
    payload = {
        "thread": [
            {
                "golden": {"calls": []},
                "actual": {"exchange": {"npc_dialogue": "I am not discussing family here."}},
                "deterministic_checks": [],
            }
        ]
    }

    with pytest.raises(ValueError, match="cited text absent from thread evidence"):
        golden_judge._validate_judge_report(report, scenario.thread_check, payload)
