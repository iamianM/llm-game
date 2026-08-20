from __future__ import annotations

import json
from pathlib import Path

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
