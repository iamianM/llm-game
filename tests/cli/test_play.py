"""CLI tests for autopilot play mode."""

from __future__ import annotations

import json
import subprocess
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from src.game.cli.commands.play import run as play_run
from src.game.cli.commands.play_autopilot import apply_autopilot_character, decide_with_autopilot
from src.game.engine.actions import ActionKind, available_actions
from src.game.engine.challenges import schedule_challenge
from src.game.state.models import Conversation, ExchangeRecord, Mood, new_game


def test_play_autopilot_runs_end_to_end_with_mock_agent(tmp_path: Path) -> None:
    trace = tmp_path / "autopilot.json"

    result = _run_play("--mock-llm", "--autopilot", "--record", str(trace))

    assert result.returncode == 0
    payload = json.loads(trace.read_text(encoding="utf-8"))
    assert payload["mode"] == "autopilot"
    assert payload["records"]
    assert payload["final_state"]["day"] >= 1


def test_play_autopilot_records_rationale_per_turn(tmp_path: Path) -> None:
    trace = tmp_path / "autopilot.json"

    result = _run_play("--mock-llm", "--autopilot", "--record", str(trace))

    assert result.returncode == 0
    payload = json.loads(trace.read_text(encoding="utf-8"))
    records = payload["records"]
    assert records
    assert all(record["agent_commits"]["player_autopilot"]["rationale"] for record in records)


def test_play_autopilot_persona_stats_are_valid() -> None:
    for persona in ("loyal", "player", "chaotic"):
        state = new_game(42)
        apply_autopilot_character(state, persona)
        stats = state.player.stats
        assert stats.charm + stats.banter + stats.eq + stats.graft + stats.loyalty == 30


def test_play_autopilot_replay_byte_identical(tmp_path: Path) -> None:
    trace = tmp_path / "autopilot.json"

    played = _run_play("--mock-llm", "--autopilot", "--record", str(trace))
    replayed = _run_play("--replay", str(trace))

    assert played.returncode == 0
    assert replayed.returncode == 0


def test_play_autopilot_closes_long_conversation() -> None:
    state = new_game(42)
    state.active_conversation = Conversation(
        target_id="chloe",
        started_on_turn=0,
        started_on_day=1,
        exchanges=[
            ExchangeRecord(
                turn_index=index,
                intent_id="go_deeper",
                player_dialogue="p",
                npc_dialogue="n",
                npc_tone="warm",
                npc_mood_after=Mood.CONTENT,
                success=True,
            )
            for index in range(6)
        ],
    )

    action, decision, _spec = decide_with_autopilot(
        state,
        available_actions(state),
        persona="loyal",
        recent_history=[],
        decider=object(),
    )

    assert action.kind in {ActionKind.RESPOND_WITH, ActionKind.END_CONVERSATION}
    assert "closes the long conversation" in decision.rationale


def test_play_autopilot_cools_down_recent_conversation_target() -> None:
    state = new_game(42)
    state.islanders[1].location_id = state.location_id
    action, decision, _spec = decide_with_autopilot(
        state,
        available_actions(state),
        persona="loyal",
        recent_history=[
            {
                "action": {"kind": "respond_with", "intent_id": "end_softly"},
                "mechanical_result": {"relationship_deltas": {"chloe": {"trust": 1}}},
            },
        ],
        decider=None,
    )

    assert action.kind is ActionKind.START_CONVERSATION
    assert action.target_id != "chloe"
    assert decision.rationale


def test_play_autopilot_resolves_challenge_before_optional_chat() -> None:
    state = new_game(42)
    state.pending_challenge = schedule_challenge(5)

    action, decision, _spec = decide_with_autopilot(
        state,
        available_actions(state),
        persona="loyal",
        recent_history=[],
        decider=object(),
    )

    assert action.kind is ActionKind.CHALLENGE_RESPONSE
    assert "before optional chats" in decision.rationale


def test_play_autopilot_advances_after_one_conversation_in_phase() -> None:
    state = new_game(42)

    action, decision, _spec = decide_with_autopilot(
        state,
        available_actions(state),
        persona="loyal",
        recent_history=[
            {
                "day": 1,
                "phase": "morning",
                "action": {"kind": "start_conversation", "target_id": "chloe"},
            },
        ],
        decider=object(),
    )

    assert action.kind is ActionKind.ADVANCE_PHASE
    assert "one focused conversation" in decision.rationale


def _run_play(*args: str) -> subprocess.CompletedProcess[str]:
    parsed = _parse_play_args(args)
    stdout = StringIO()
    with redirect_stdout(stdout):
        returncode = play_run(parsed)
    return subprocess.CompletedProcess(
        ["play", *args],
        returncode,
        stdout.getvalue(),
        "",
    )


def _parse_play_args(args: tuple[str, ...]) -> SimpleNamespace:
    parsed = SimpleNamespace(
        seed=42,
        mock_llm=False,
        trace=False,
        record=None,
        replay=None,
        autopilot=False,
        persona="loyal",
        max_turns=120,
    )
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--mock-llm":
            parsed.mock_llm = True
        elif arg == "--autopilot":
            parsed.autopilot = True
        elif arg in {"--record", "--replay", "--persona", "--max-turns"}:
            value = args[index + 1]
            if arg == "--record":
                parsed.record = value
            elif arg == "--replay":
                parsed.replay = value
            elif arg == "--persona":
                parsed.persona = value
            else:
                parsed.max_turns = int(value)
            index += 1
        else:
            raise AssertionError(f"unsupported test play arg: {arg}")
        index += 1
    return parsed
