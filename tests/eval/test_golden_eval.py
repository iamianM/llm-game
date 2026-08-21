from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from src.game.agents.runtime import (
    AgentValidationError,
    record_agent_trace,
)
from src.game.agents.turn_agents import mock_turn_agents
from src.game.eval import golden_runner
from src.game.eval.golden_runner import load_golden_scenarios, run_golden_eval


def test_golden_eval_pack_writes_mock_report(tmp_path: Path) -> None:
    scenarios = load_golden_scenarios(Path("evals/llm/scenarios"))

    result = run_golden_eval(
        scenarios,
        out=tmp_path / "llm-eval",
        real_llm=False,
        judge=False,
    )

    assert result.failed == 0
    assert result.scenario_count >= 18
    assert result.passed == result.scenario_count
    assert result.worker_count == min(result.scenario_count, 8)
    report = tmp_path / "llm-eval" / "index.html"
    run_json = tmp_path / "llm-eval" / "artifacts" / "run.json"
    assert report.is_file()
    assert run_json.is_file()
    payload = json.loads(run_json.read_text(encoding="utf-8"))
    assert payload["passed"] == result.scenario_count
    assert payload["worker_count"] == result.worker_count
    assert all(
        scenario["thread_expectation"]["id"] == "thread_acceptance"
        for scenario in payload["scenarios"]
    )
    assert all(scenario["thread_check"] is None for scenario in payload["scenarios"])
    assert all("thread_checks" not in scenario for scenario in payload["scenarios"])
    html = report.read_text(encoding="utf-8")
    assert "First Chat With Every Starting NPC" in html
    assert "Thread evaluation" in html
    assert "Judge not run" in html
    assert "dashboard-shell" in html
    assert "scenario-rail" in html
    assert "scenario-workspace" in html


def test_golden_scenarios_define_exactly_one_semantic_thread_check() -> None:
    scenarios = load_golden_scenarios(Path("evals/llm/scenarios"))

    assert all(scenario.thread_check.id == "thread_acceptance" for scenario in scenarios)
    assert all(scenario.thread_check.criteria for scenario in scenarios)
    assert all(
        "judge_checks" not in turn.model_fields_set
        for scenario in scenarios
        for turn in scenario.turns
    )


def test_golden_eval_records_failed_turn_and_attempt_traces(
    tmp_path: Path,
    monkeypatch,
) -> None:
    scenario = load_golden_scenarios(Path("evals/llm/scenarios"))[0]

    def boom(*_args, **_kwargs):
        record_agent_trace(
            agent_name="scripted_failure",
            model="test-model",
            prompt_path="test",
            response=object(),
            output=None,
        )
        raise AgentValidationError("scripted story failure")

    base = mock_turn_agents()
    failed = replace(
        base,
        heartbreaker_voice=boom,
        contextual_options=boom,
        event_narrator=boom,
        conversation_curator=boom,
        resort_orchestrator=boom,
        background_dialogue=boom,
    )
    monkeypatch.setattr(golden_runner, "mock_turn_agents", lambda: failed)
    out = tmp_path / "failed-eval"

    result = run_golden_eval(
        [scenario],
        out=out,
        real_llm=False,
        judge=False,
        max_workers=1,
    )

    assert result.failed == 1
    failed_turn = result.scenarios[0].turns[0]
    assert failed_turn.error == "scripted story failure"
    assert failed_turn.record["agent_traces"][0]["agent_name"] == "scripted_failure"
    trace = json.loads(
        (out / "artifacts" / f"{scenario.id}-trace.json").read_text(encoding="utf-8")
    )
    assert trace[0]["error"] == "scripted story failure"
    assert trace[0]["agent_traces"][0]["agent_name"] == "scripted_failure"
