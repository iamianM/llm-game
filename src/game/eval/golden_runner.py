"""Runner for authored golden LLM eval scenarios."""

from __future__ import annotations

import contextvars
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast

import yaml

from src.api.session import AgentBundle
from src.game.agents.runtime import recover_agent_traces_after_error
from src.game.cli.commands.play_recording import record_from_turn
from src.game.engine.character_creation import create_character
from src.game.engine.phases import PHASE_BUDGETS
from src.game.engine.turn import run_turn
from src.game.eval.golden_checks import run_deterministic_check
from src.game.eval.golden_judge import run_judge_checks
from src.game.eval.golden_models import (
    CheckResultValue,
    GoldenCheckResult,
    GoldenEvalRun,
    GoldenEvalScenario,
    GoldenScenarioResult,
    GoldenTurnResult,
    GoldenTurnSpec,
)
from src.game.eval.golden_report import render_golden_eval_html
from src.game.state.models import GameState, new_game
from src.game.state.phase_clock import PhaseClock
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
    if not scenarios:
        results: list[GoldenScenarioResult] = []
    else:
        worker_count = max_workers if max_workers is not None else min(len(scenarios), 8)

        def _run_isolated(scenario: GoldenEvalScenario) -> GoldenScenarioResult:
            return contextvars.copy_context().run(
                _run_scenario, scenario, out=out, real_llm=real_llm, judge=judge
            )

        if worker_count <= 1:
            results = [_run_isolated(scenario) for scenario in scenarios]
        else:
            with ThreadPoolExecutor(max_workers=worker_count) as pool:
                results = list(pool.map(_run_isolated, scenarios))
    passed = sum(1 for result in results if result.status == "pass")
    failed = sum(1 for result in results if result.status == "fail")
    cannot_determine = sum(1 for result in results if result.status == "cannot_determine")
    run = GoldenEvalRun(
        llm_mode="real" if real_llm else "mock",
        judge_enabled=judge,
        scenario_count=len(results),
        passed=passed,
        failed=failed,
        cannot_determine=cannot_determine,
        scenarios=results,
    )
    (out / "artifacts" / "run.json").write_text(run.model_dump_json(indent=2), encoding="utf-8")
    (out / "index.html").write_text(render_golden_eval_html(run), encoding="utf-8")
    return run


def _run_scenario(
    scenario: GoldenEvalScenario,
    *,
    out: Path,
    real_llm: bool,
    judge: bool,
) -> GoldenScenarioResult:
    state = _new_scenario_state(scenario)
    rng = SeededRng(scenario.seed)
    agents = AgentBundle.live() if real_llm else AgentBundle.mock()
    if real_llm and not scenario.live_villa_life:
        agents.villa_orchestrator = None
        agents.background_dialogue = None
    turn_results: list[GoldenTurnResult] = []
    records: list[dict[str, object]] = []
    for turn_spec in scenario.turns:
        _apply_turn_arrangements(state, turn_spec)
        input_hash = state_hash(state_hash_payload(state))
        pre_state = state.model_copy(deep=True)
        try:
            turn = run_turn(
                state,
                turn_spec.action,
                rng,
                islander_voice=agents.islander_voice,
                contextual_options=agents.contextual_options,
                event_narrator=agents.event_narrator,
                conversation_curator=agents.conversation_curator,
                villa_orchestrator=agents.villa_orchestrator,
                background_dialogue=agents.background_dialogue,
            )
            state = turn.state
            record = cast(dict[str, object], record_from_turn(input_hash, turn_spec.action, turn))
            records.append(record)
            checks = _run_turn_checks(turn_spec, turn, "real" if real_llm else "mock", pre_state)
            if judge:
                checks.extend(
                    run_judge_checks(
                        scenario_title=scenario.title,
                        scenario_goal=scenario.goal,
                        scenario_context=scenario.judge_context,
                        turn_spec=turn_spec,
                        record=record,
                        prior_records=records[:-1],
                        prompt_out=out / "judge-prompts" / f"{scenario.id}-{turn_spec.id}.txt",
                    )
                )
            turn_results.append(
                GoldenTurnResult(
                    id=turn_spec.id,
                    action=turn_spec.action.model_dump(mode="json"),
                    arrangements=_turn_arrangements_payload(turn_spec),
                    expected_tools=_expected_tools(turn_spec, scenario),
                    golden=turn_spec.golden,
                    judge_checks=turn_spec.judge_checks,
                    input_hash=input_hash,
                    output_hash=turn.state_hash,
                    record=record,
                    checks=checks,
                )
            )
        except Exception as exc:
            error_record = {
                "action": turn_spec.action.model_dump(mode="json"),
                "error": str(exc),
                "agent_traces": [
                    trace.model_dump(mode="json")
                    for trace in recover_agent_traces_after_error()
                ],
            }
            turn_results.append(
                GoldenTurnResult(
                    id=turn_spec.id,
                    action=turn_spec.action.model_dump(mode="json"),
                    arrangements=_turn_arrangements_payload(turn_spec),
                    expected_tools=_expected_tools(turn_spec, scenario),
                    golden=turn_spec.golden,
                    judge_checks=turn_spec.judge_checks,
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
            break
    (out / "artifacts" / f"{scenario.id}-trace.json").write_text(
        json.dumps(records, indent=2),
        encoding="utf-8",
    )
    return GoldenScenarioResult(
        id=scenario.id,
        title=scenario.title,
        goal=scenario.goal,
        status=_scenario_status(turn_results),
        turns=turn_results,
    )


def _new_scenario_state(scenario: GoldenEvalScenario) -> GameState:
    state = new_game(scenario.seed, player_stats=scenario.player_stats)
    if scenario.initial_day is not None:
        state.day = scenario.initial_day
    if scenario.initial_phase is not None:
        state.phase = scenario.initial_phase
        state.phase_clock = PhaseClock(
            phase=scenario.initial_phase.value,
            budget_minutes=PHASE_BUDGETS[scenario.initial_phase],
        )
    if scenario.initial_phase_budget_minutes is not None:
        state.phase_clock.budget_minutes = scenario.initial_phase_budget_minutes
    if scenario.initial_location is not None:
        state.location_id = scenario.initial_location
    if scenario.initial_relationships is not None:
        for islander in state.islanders:
            relationship = scenario.initial_relationships.get(islander.id)
            if relationship is not None:
                islander.relationship = relationship.model_copy(deep=True)
    if scenario.initial_couples is not None:
        state.couples = [couple.model_copy(deep=True) for couple in scenario.initial_couples]
    if scenario.initial_npc_conversations is not None:
        state.npc_conversations = [
            conversation.model_copy(deep=True)
            for conversation in scenario.initial_npc_conversations
        ]
    if scenario.character_creation is not None:
        create_character(
            state,
            archetype_id=scenario.character_creation.archetype_id,
            gender=scenario.character_creation.gender,
            stats=scenario.character_creation.stats,
            rerolled=scenario.character_creation.rerolled,
        )
    return state


def _apply_turn_arrangements(state: GameState, turn_spec: GoldenTurnSpec) -> None:
    if turn_spec.arrange_player_location is not None:
        state.location_id = turn_spec.arrange_player_location
    for islander in state.islanders:
        location = turn_spec.arrange_npc_locations.get(islander.id)
        if location is not None:
            islander.location_id = location
    if turn_spec.arrange_active_conversation is not None:
        state.active_conversation = turn_spec.arrange_active_conversation.model_copy(deep=True)


def _turn_arrangements_payload(turn_spec: GoldenTurnSpec) -> dict[str, object]:
    payload: dict[str, object] = {}
    if turn_spec.arrange_player_location is not None:
        payload["player_location"] = turn_spec.arrange_player_location.value
    if turn_spec.arrange_npc_locations:
        payload["npc_locations"] = {
            islander_id: location.value
            for islander_id, location in turn_spec.arrange_npc_locations.items()
        }
    return payload


def _expected_tools(turn_spec: GoldenTurnSpec, scenario: GoldenEvalScenario) -> list[str]:
    kind = turn_spec.action.kind.value
    if kind in {"start_conversation", "respond_with"}:
        tools = ["Islander Voice -> Exchange", "Contextual Options -> ContextualBespoke"]
        if scenario.live_villa_life:
            tools.extend(["Villa Orchestrator -> VillaUpdate", "Background Dialogue -> BackgroundExchange"])
        return tools
    if kind == "end_conversation":
        tools = ["Conversation Curator -> MemoryBatch"]
        if scenario.live_villa_life:
            tools.extend(["Villa Orchestrator -> VillaUpdate", "Background Dialogue -> BackgroundExchange"])
        return tools
    if kind in {"ambient", "join_gather", "recouple", "propose_recouple", "challenge_response"}:
        tools = ["Event Narrator -> EventNarration"]
        if scenario.live_villa_life:
            tools.extend(["Villa Orchestrator -> VillaUpdate", "Background Dialogue -> BackgroundExchange"])
        return tools
    return ["Engine-only turn"]


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


def _scenario_status(turns: list[GoldenTurnResult]) -> CheckResultValue:
    results = [check.result for turn in turns for check in turn.checks]
    if any(result == "fail" for result in results):
        return "fail"
    if any(result == "cannot_determine" for result in results):
        return "cannot_determine"
    return "pass"
