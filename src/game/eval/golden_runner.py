"""Runner for authored golden LLM eval scenarios."""

from __future__ import annotations

import contextvars
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast

import yaml

from src.game.agents.runtime import recover_agent_traces_after_error
from src.game.agents.turn_agents import live_turn_agents, mock_turn_agents
from src.game.cli.commands.play_recording import record_from_turn
from src.game.engine.turn import run_turn
from src.game.eval.golden_checks import run_deterministic_check
from src.game.eval.golden_costs import CallCost, RunAccounting, summarize_call, summarize_calls
from src.game.eval.golden_judge import run_thread_check
from src.game.eval.golden_models import (
    CheckResultValue,
    ExecutionModel,
    GoldenCheckResult,
    GoldenEvalRun,
    GoldenEvalScenario,
    GoldenScenarioResult,
    GoldenTurnResult,
    JudgeTrace,
    ThreadCheckSpec,
)
from src.game.eval.golden_replay import (
    apply_turn_arrangements,
    build_isolated_turn_input,
    new_scenario_state,
    turn_arrangements_payload,
)
from src.game.eval.golden_report import render_golden_eval_html
from src.game.eval.golden_showcase import build_golden_eval_showcase
from src.game.state.models import GameState
from src.game.state.rng import SeededRng
from src.game.state.snapshot import state_hash, state_hash_payload


def load_golden_scenarios(root: Path) -> list[GoldenEvalScenario]:
    """Load one scenario file or every YAML scenario under a directory."""
    paths = [root] if root.is_file() else sorted(root.glob("*.yaml"))
    if not paths:
        raise ValueError(f"no golden eval scenarios found: {root}")
    return [load_golden_scenario(path) for path in paths]


def load_golden_scenario(path: Path) -> GoldenEvalScenario:
    """Load and validate one golden eval YAML file."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"golden eval scenario must be a mapping: {path}")
    return GoldenEvalScenario.model_validate(cast(dict[str, object], raw))


def run_golden_eval(
    scenarios: list[GoldenEvalScenario],
    *,
    out: Path,
    real_llm: bool,
    judge: bool,
    max_workers: int | None = None,
    execution_model: ExecutionModel = "isolated_golden_replay",
) -> GoldenEvalRun:
    """Run scenarios concurrently and write JSON + HTML review artifacts.

    Scenarios are independent (fresh state + seeded RNG per scenario, scenario-
    scoped artifact paths), so we run them in a thread pool. Each scenario gets
    its own ``contextvars`` context so the agent-trace ContextVar does not race
    across threads.
    """
    out.mkdir(parents=True, exist_ok=True)
    (out / "artifacts").mkdir(exist_ok=True)
    (out / "judge-prompts").mkdir(exist_ok=True)
    worker_count = _resolved_worker_count(len(scenarios), max_workers)
    if not scenarios:
        results: list[GoldenScenarioResult] = []
    else:

        def _run_one(scenario: GoldenEvalScenario) -> GoldenScenarioResult:
            return contextvars.copy_context().run(
                _run_scenario,
                scenario,
                out=out,
                real_llm=real_llm,
                judge=judge,
                execution_model=execution_model,
            )

        if worker_count <= 1:
            results = [_run_one(scenario) for scenario in scenarios]
        else:
            with ThreadPoolExecutor(max_workers=worker_count) as pool:
                results = list(pool.map(_run_one, scenarios))
    passed = sum(1 for result in results if result.status == "pass")
    failed = sum(1 for result in results if result.status == "fail")
    cannot_determine = sum(1 for result in results if result.status == "cannot_determine")
    accounting = _run_accounting(results)
    run = GoldenEvalRun(
        llm_mode="real" if real_llm else "mock",
        judge_enabled=judge,
        scenario_count=len(results),
        worker_count=worker_count,
        passed=passed,
        failed=failed,
        cannot_determine=cannot_determine,
        accounting=accounting,
        scenarios=results,
        execution_model=execution_model,
    )
    (out / "artifacts" / "run.json").write_text(run.model_dump_json(indent=2), encoding="utf-8")
    (out / "index.html").write_text(render_golden_eval_html(run), encoding="utf-8")
    (out / "showcase.json").write_text(
        build_golden_eval_showcase(run).model_dump_json(indent=2),
        encoding="utf-8",
    )
    return run


def _resolved_worker_count(scenario_count: int, max_workers: int | None) -> int:
    if scenario_count == 0:
        return 0
    if max_workers is None:
        return min(scenario_count, 8)
    if max_workers < 1:
        raise ValueError("--max-workers must be at least 1")
    return min(max_workers, scenario_count)


def _run_accounting(results: list[GoldenScenarioResult]) -> RunAccounting:
    agent_calls: list[CallCost] = []
    judge_calls: list[CallCost] = []
    for result in results:
        for turn in result.turns:
            record = turn.record if isinstance(turn.record, dict) else {}
            traces = record.get("agent_traces")
            if not isinstance(traces, list):
                continue
            for trace in traces:
                if not isinstance(trace, dict):
                    continue
                usage = trace.get("usage")
                agent_calls.append(
                    summarize_call(
                        str(trace.get("model", "")),
                        usage if isinstance(usage, dict) else {},
                    )
                )
        judge = result.judge_trace
        if judge is not None:
            judge_calls.append(
                summarize_call(
                    judge.model,
                    {
                        key: value
                        for key in (
                            "input_tokens",
                            "cached_input_tokens",
                            "cache_write_tokens",
                            "output_tokens",
                            "reasoning_tokens",
                            "total_tokens",
                        )
                        if (value := getattr(judge, key)) is not None
                    },
                )
            )
    return RunAccounting(
        game_agents=summarize_calls(agent_calls),
        judges=summarize_calls(judge_calls),
        total=summarize_calls([*agent_calls, *judge_calls]),
    )


def _run_scenario(
    scenario: GoldenEvalScenario,
    *,
    out: Path,
    real_llm: bool,
    judge: bool,
    execution_model: ExecutionModel,
) -> GoldenScenarioResult:
    agents = (
        live_turn_agents("full" if scenario.live_resort_life else "no_resort_life")
        if real_llm
        else mock_turn_agents()
    )
    turn_results: list[GoldenTurnResult] = []
    records: list[dict[str, object]] = []
    causal_state = new_scenario_state(scenario) if execution_model == "causal_rollout" else None
    causal_rng = SeededRng(scenario.seed) if execution_model == "causal_rollout" else None
    for target_index, turn_spec in enumerate(scenario.turns):
        if execution_model == "isolated_golden_replay":
            isolated = build_isolated_turn_input(scenario, target_index=target_index)
            state = isolated.state
            rng = isolated.rng
            input_source = "fresh_scenario_state" if target_index == 0 else "reviewed_prefix"
            input_turn_ids = isolated.replayed_turn_ids
        else:
            if causal_state is None or causal_rng is None:
                raise AssertionError("causal rollout state was not initialized")
            state = causal_state
            rng = causal_rng
            input_source = "fresh_scenario_state" if target_index == 0 else "actual_prefix"
            input_turn_ids = [turn.id for turn in turn_results]
        apply_turn_arrangements(state, turn_spec)
        input_hash = state_hash(state_hash_payload(state))
        pre_state = state.model_copy(deep=True)
        try:
            turn = run_turn(state, turn_spec.action, rng, agents)
            state = turn.state
            if execution_model == "causal_rollout":
                causal_state = state
            record = cast(dict[str, object], record_from_turn(input_hash, turn_spec.action, turn))
            records.append(record)
            checks = _run_turn_checks(turn_spec, turn, "real" if real_llm else "mock", pre_state)
            turn_results.append(
                GoldenTurnResult(
                    id=turn_spec.id,
                    action=turn_spec.action.model_dump(mode="json"),
                    arrangements=turn_arrangements_payload(turn_spec),
                    input_source=input_source,
                    input_turn_ids=input_turn_ids,
                    golden=turn_spec.golden,
                    input_hash=input_hash,
                    output_hash=turn.state_hash,
                    record=record,
                    checks=checks,
                )
            )
        except Exception as exc:
            error_record: dict[str, object] = {
                "action": turn_spec.action.model_dump(mode="json"),
                "error": str(exc),
                "agent_traces": [
                    trace.model_dump(mode="json") for trace in recover_agent_traces_after_error()
                ],
            }
            records.append(error_record)
            turn_results.append(
                GoldenTurnResult(
                    id=turn_spec.id,
                    action=turn_spec.action.model_dump(mode="json"),
                    arrangements=turn_arrangements_payload(turn_spec),
                    input_source=input_source,
                    input_turn_ids=input_turn_ids,
                    golden=turn_spec.golden,
                    input_hash=input_hash,
                    record=error_record,
                    checks=[
                        GoldenCheckResult(
                            id="turn_runtime_error",
                            kind="deterministic",
                            result="fail",
                            reason=str(exc),
                            turn_id=turn_spec.id,
                        )
                    ],
                    error=str(exc),
                )
            )
            if execution_model == "causal_rollout":
                break
    (out / "artifacts" / f"{scenario.id}-trace.json").write_text(
        json.dumps(records, indent=2),
        encoding="utf-8",
    )
    thread_check: GoldenCheckResult | None = None
    judge_trace: JudgeTrace | None = None
    if judge:
        try:
            thread_check, judge_trace = run_thread_check(
                scenario=_judge_scenario(scenario, execution_model),
                records=records,
                deterministic_checks=[turn.checks for turn in turn_results],
                prompt_out=out / "judge-prompts" / f"{scenario.id}.json",
                execution_model=execution_model,
            )
        except Exception as exc:
            thread_check = GoldenCheckResult(
                id=_thread_check_for(scenario, execution_model).id,
                kind="judge",
                result="cannot_determine",
                reason=f"thread judge failed: {exc}",
                severity=_thread_check_for(scenario, execution_model).severity,
            )
    return GoldenScenarioResult(
        id=scenario.id,
        title=scenario.title,
        question=scenario.question,
        category=scenario.category,
        goal=scenario.goal,
        status=_scenario_status(turn_results, thread_check),
        thread_expectation=_thread_check_for(scenario, execution_model),
        thread_check=thread_check,
        judge_trace=judge_trace,
        turns=turn_results,
    )


def _thread_check_for(
    scenario: GoldenEvalScenario,
    execution_model: ExecutionModel,
) -> ThreadCheckSpec:
    if execution_model == "causal_rollout":
        if scenario.causal_thread_check is None:
            raise ValueError(
                f"scenario {scenario.id!r} does not define causal_thread_check"
            )
        return scenario.causal_thread_check
    return scenario.thread_check


def _judge_scenario(
    scenario: GoldenEvalScenario,
    execution_model: ExecutionModel,
) -> GoldenEvalScenario:
    return scenario.model_copy(update={"thread_check": _thread_check_for(scenario, execution_model)})


_UNIVERSAL_CHECKS: tuple[str, ...] = ("engine_state_invariants_preserved",)


def _run_turn_checks(
    turn_spec: object,
    turn: object,
    llm_mode: str,
    pre_state: GameState,
) -> list[GoldenCheckResult]:
    from src.game.eval.golden_models import GoldenTurnSpec

    if not isinstance(turn_spec, GoldenTurnSpec):
        raise TypeError("turn_spec must be GoldenTurnSpec")
    check_ids = list(turn_spec.checks)
    for universal in _UNIVERSAL_CHECKS:
        if universal not in check_ids:
            check_ids.append(universal)
    return [
        run_deterministic_check(
            check_id,
            turn_spec=turn_spec,
            turn=turn,
            llm_mode=llm_mode,
            pre_state=pre_state,
        )
        for check_id in check_ids
    ]


def _scenario_status(
    turns: list[GoldenTurnResult],
    thread_check: GoldenCheckResult | None,
) -> CheckResultValue:
    checks = [check for turn in turns for check in turn.checks]
    if thread_check is not None and thread_check.severity == "blocking":
        checks.append(thread_check)
    results = [check.result for check in checks]
    if any(result == "fail" for result in results):
        return "fail"
    if any(result == "cannot_determine" for result in results):
        return "cannot_determine"
    return "pass"
