"""Golden deterministic evals for Blackfen Road."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.blackfen.models import RunStatus
from src.blackfen.scenario import ActionScript, run_action_script
from src.blackfen.trace import build_trace_package, save_trace

DEFAULT_EVAL_DIR = Path("evals") / "blackfen" / "scenarios"


class BlackfenEvalScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    seed: int
    class_id: str = "fighter"
    player_name: str = "You"
    intent: str
    actions: list[str] = Field(min_length=1)
    expected_hash: str
    expected_status: RunStatus


class BlackfenEvalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    passed: bool
    final_hash: str
    expected_hash: str
    final_status: RunStatus
    expected_status: RunStatus
    fun_score: int
    notes: list[str]
    trace_path: str | None = None


def load_eval_scenario(path: Path) -> BlackfenEvalScenario:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"eval scenario must be a YAML mapping: {path}")
    return BlackfenEvalScenario.model_validate(cast(dict[str, object], raw))


def run_eval_scenario(scenario: BlackfenEvalScenario, *, trace_dir: Path | None = None) -> BlackfenEvalResult:
    script = ActionScript(name=scenario.name, seed=scenario.seed, player_name=scenario.player_name, class_id=scenario.class_id, actions=scenario.actions, expected_hash=scenario.expected_hash)
    result = run_action_script(script)
    trace = build_trace_package(result, name=scenario.name)
    trace_path = str(save_trace(trace, trace_dir / f"{scenario.name}.json")) if trace_dir is not None else None
    passed = result.final_hash == scenario.expected_hash and result.state.status is scenario.expected_status
    return BlackfenEvalResult(
        name=scenario.name,
        passed=passed,
        final_hash=result.final_hash,
        expected_hash=scenario.expected_hash,
        final_status=result.state.status,
        expected_status=scenario.expected_status,
        fun_score=trace.fun_score,
        notes=trace.review_notes,
        trace_path=trace_path,
    )


def run_eval_suite(*, scenario_dir: Path = DEFAULT_EVAL_DIR, out_dir: Path | None = None) -> list[BlackfenEvalResult]:
    paths = sorted(path for path in scenario_dir.glob("*.yaml") if path.name != "FORMAT.md")
    if not paths:
        raise FileNotFoundError(f"no Blackfen eval scenarios found in {scenario_dir}")
    trace_dir = out_dir / "traces" if out_dir is not None else None
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
    results = [run_eval_scenario(load_eval_scenario(path), trace_dir=trace_dir) for path in paths]
    if out_dir is not None:
        (out_dir / "results.json").write_text(json.dumps([result.model_dump(mode="json") for result in results], indent=2, sort_keys=True), encoding="utf-8")
    return results
