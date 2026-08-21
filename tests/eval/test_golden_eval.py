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
from src.game.eval.golden_showcase import GoldenEvalShowcase, build_golden_eval_showcase


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
    showcase_json = tmp_path / "llm-eval" / "showcase.json"
    assert report.is_file()
    assert run_json.is_file()
    assert showcase_json.is_file()
    payload = json.loads(run_json.read_text(encoding="utf-8"))
    assert payload["passed"] == result.scenario_count
    assert payload["worker_count"] == result.worker_count
    assert payload["accounting"]["total"]["usage"]["total_tokens"] == 0
    assert all(
        scenario["thread_expectation"]["id"] == "thread_acceptance"
        for scenario in payload["scenarios"]
    )
    assert all(scenario["thread_check"] is None for scenario in payload["scenarios"])
    assert all("thread_checks" not in scenario for scenario in payload["scenarios"])
    showcase = json.loads(showcase_json.read_text(encoding="utf-8"))
    assert showcase["turn_count"] == sum(len(scenario.turns) for scenario in result.scenarios)
    assert showcase["agent_call_count"] == 0
    assert {scenario["category"] for scenario in showcase["scenarios"]} == {
        "conversation",
        "social_dynamics",
        "pairing_and_endings",
        "special_events",
        "challenges",
    }
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
    assert all(turn.golden.criteria for scenario in scenarios for turn in scenario.turns)


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


def test_public_showcase_uses_an_explicit_safe_allowlist(tmp_path: Path) -> None:
    scenario = load_golden_scenarios(Path("evals/llm/scenarios/conversation-continuity-exit.yaml"))
    run = run_golden_eval(scenario, out=tmp_path / "eval", real_llm=False, judge=False)
    record = run.scenarios[0].turns[0].record
    assert record is not None
    run.scenarios[0].turns[0].golden.calls[0].output["prompt_path"] = (
        "C:\\private\\golden.md"
    )
    record["response_id"] = "secret-response"
    record["input_hash"] = "secret-hash"
    record["prompt_path"] = "C:\\private\\prompt.md"
    record["agent_traces"] = [
        {
            "agent_name": "heartbreaker_voice",
            "model": "safe-model",
            "reasoning_effort": "low",
            "output_type": "Exchange",
            "response_id": "secret-response",
            "prompt_path": "C:\\private\\prompt.md",
            "input": {"api_key": "secret-key"},
            "output": {"duplicate": "do not publish"},
            "latency_ms": 10,
            "usage": {
                "input_tokens": 12,
                "cached_input_tokens": 4,
                "output_tokens": 8,
                "total_tokens": 20,
            },
            "reasoning_summaries": [{"item_id": "r1", "texts": ["Compared tone and continuity."]}],
        }
    ]

    showcase = build_golden_eval_showcase(run)
    encoded = showcase.model_dump_json()

    assert "safe-model" in encoded
    assert "secret" not in encoded
    assert "prompt_path" not in encoded
    assert "response_id" not in encoded
    assert "input_hash" not in encoded
    assert "duplicate" not in encoded
    assert showcase.scenarios[0].turns[0].traces[0].input_tokens == 12
    assert showcase.scenarios[0].turns[0].traces[0].cached_input_tokens == 4
    assert showcase.scenarios[0].turns[0].traces[0].output_tokens == 8
    assert showcase.scenarios[0].turns[0].traces[0].reasoning_summaries == [
        "Compared tone and continuity."
    ]
    assert showcase.accounting.game_agents.cost.kind == "unavailable"
    assert showcase.scenarios[0].turns[0].action.startswith("start_conversation | target chloe")


def test_tracked_showcase_is_a_complete_reviewed_public_run() -> None:
    path = Path("web/data/evals/latest.json")
    encoded = path.read_text(encoding="utf-8")
    showcase = GoldenEvalShowcase.model_validate_json(encoded)

    assert showcase.llm_mode == "real"
    assert showcase.judge_enabled
    assert all(scenario.judge is not None for scenario in showcase.scenarios)
    assert showcase.passed + showcase.failed + showcase.cannot_determine == len(showcase.scenarios)
    assert showcase.turn_count == sum(len(scenario.turns) for scenario in showcase.scenarios)
    traces = [
        trace for scenario in showcase.scenarios for turn in scenario.turns for trace in turn.traces
    ]
    assert showcase.agent_call_count == len(traces)
    assert all(trace.output is not None for trace in traces)
    judge_tokens = sum(scenario.judge.total_tokens or 0 for scenario in showcase.scenarios if scenario.judge)
    assert showcase.total_tokens == sum(trace.total_tokens or 0 for trace in traces) + judge_tokens
    assert showcase.accounting.total.usage.total_tokens == showcase.total_tokens
    source_categories = {
        scenario.id: scenario.category
        for scenario in load_golden_scenarios(Path("evals/llm/scenarios"))
    }
    assert {scenario.id: scenario.category for scenario in showcase.scenarios} == source_categories
    source_goldens = {
        (scenario.id, turn.id): [
            (call.agent, call.output_type) for call in turn.golden.calls
        ]
        for scenario in load_golden_scenarios(Path("evals/llm/scenarios"))
        for turn in scenario.turns
    }
    published_goldens = {
        (scenario.id, turn.id): [
            (call.agent, call.output_type) for call in turn.golden.calls
        ]
        for scenario in showcase.scenarios
        for turn in scenario.turns
    }
    actual_calls = {
        (scenario.id, turn.id): [
            (trace.agent, trace.output_type) for trace in turn.traces
        ]
        for scenario in showcase.scenarios
        for turn in scenario.turns
    }
    assert published_goldens == source_goldens
    assert published_goldens == actual_calls
    for scenario in showcase.scenarios:
        for turn in scenario.turns:
            assert all(
                set(golden.output) == set(actual.output or {})
                for golden, actual in zip(turn.golden.calls, turn.traces, strict=True)
            )

    lowered = encoded.lower()
    forbidden_fragments = (
        "response_id",
        "prompt_path",
        "prompt_sha",
        "input_hash",
        "output_hash",
        "api_key",
        "authorization",
        "bearer ",
        "c:\\\\users\\",
        "/home/",
        "/users/",
        "sk-",
    )
    assert not any(fragment in lowered for fragment in forbidden_fragments)
