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
    assert result.scenario_count >= 9
    assert result.passed == result.scenario_count
    report = tmp_path / "llm-eval" / "index.html"
    run_json = tmp_path / "llm-eval" / "artifacts" / "run.json"
    assert report.is_file()
    assert run_json.is_file()
    payload = json.loads(run_json.read_text(encoding="utf-8"))
    assert payload["passed"] == result.scenario_count
    assert "First Chat With Every Starting NPC" in report.read_text(encoding="utf-8")
