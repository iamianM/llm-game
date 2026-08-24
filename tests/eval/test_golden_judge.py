from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import httpx
from openai import APIConnectionError

from src.game.eval import golden_judge
from src.game.eval.golden_judge import JudgeReport, build_thread_judge_prompt, run_thread_check
from src.game.eval.golden_models import GoldenCheckResult
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
    assert all(
        turn["deterministic_checks"][0]["id"] == "conversation_active"
        for turn in payload["thread"]
    )


def test_thread_judge_retries_transient_connection_failure(monkeypatch, tmp_path: Path) -> None:
    scenario = load_golden_scenario(Path("evals/llm/scenarios/opening-ceremony.yaml"))
    response = SimpleNamespace(
        output_parsed=JudgeReport(result="pass", reason="faithful"),
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
                raise APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
            return response

    responses = FakeResponses()
    monkeypatch.setattr(golden_judge, "build_game_client", lambda: SimpleNamespace(responses=responses))
    monkeypatch.setattr(golden_judge, "sleep", lambda _seconds: None)

    result, trace = run_thread_check(
        scenario=scenario,
        records=[{}],
        deterministic_checks=[[]],
        prompt_out=tmp_path / "judge.json",
    )

    assert result.result == "pass"
    assert trace.attempts == 2
    assert trace.retry_errors and trace.retry_errors[0].startswith("APIConnectionError:")
