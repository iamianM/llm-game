"""Turn-by-turn CLI playtest sessions for subagents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.game.agents.background_dialogue import OpenAIBackgroundDialogue
from src.game.agents.contextual_options import ContextualOptionsAgent
from src.game.agents.conversation_curator import OpenAIConversationCurator
from src.game.agents.event_narrator import OpenAIEventNarrator
from src.game.agents.heartbreaker_voice import OpenAIHeartbreakerVoice
from src.game.agents.resort_orchestrator import OpenAIResortOrchestrator
from src.game.cli.commands.play_recording import record_from_turn, write_recording
from src.game.cli.commands.play_render import print_actions, print_state, print_turn
from src.game.engine.actions import ActionKind, PlayerAction, available_actions
from src.game.engine.character_creation import DEFAULT_ARCHETYPE_STATS, create_character
from src.game.engine.intents import IntentCategory, available_intents_for
from src.game.engine.turn import run_turn
from src.game.state.models import GameState, Gender, PlayerStats, new_game
from src.game.state.rng import SeededRng
from src.game.state.snapshot import (
    load_checkpoint,
    save_named_checkpoint,
    state_hash,
    state_hash_payload,
)
from src.game.state.trace import TraceMode

SESSION_DIR = Path(".game_sessions")


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the play-session command."""
    parser = subparsers.add_parser(
        "play-session",
        help="run a persisted turn-by-turn CLI playtest session",
    )
    session_sub = parser.add_subparsers(dest="session_command", required=True)

    start = session_sub.add_parser("start", help="start a persisted playtest session")
    start.add_argument("--name", required=True)
    start.add_argument("--seed", type=int, default=42)
    start.add_argument("--record", default=None)
    start.add_argument("--archetype", default="loyal_friend")
    start.add_argument("--gender", choices=[g.value for g in Gender], default="man")
    start.add_argument("--stats", help="comma-separated charm,banter,eq,spark,loyalty")
    start.add_argument("--mock-llm", action="store_true")
    start.set_defaults(func=_start)

    resume = session_sub.add_parser("resume", help="branch a session from a saved checkpoint")
    resume.add_argument("--name", required=True)
    resume.add_argument("--from-checkpoint", required=True)
    resume.add_argument("--record", default=None)
    resume.add_argument("--mock-llm", action="store_true")
    resume.set_defaults(func=_resume)

    show = session_sub.add_parser("show", help="show state and available actions")
    show.add_argument("--name", required=True)
    show.set_defaults(func=_show)

    choose = session_sub.add_parser("choose", help="apply one visible action by index")
    choose.add_argument("--name", required=True)
    choose.add_argument("--action", type=int, required=True, help="1-based visible action index")
    choose.add_argument("--intent", type=int, help="1-based intent index for Start Conversation")
    choose.set_defaults(func=_choose)

    checkpoint = session_sub.add_parser("checkpoint", help="save a named checkpoint")
    checkpoint.add_argument("--name", required=True)
    checkpoint.add_argument("--checkpoint", required=True)
    checkpoint.set_defaults(func=_checkpoint)


def _start(args: argparse.Namespace) -> int:
    state = new_game(args.seed)
    stats = _parse_stats(args.stats, args.archetype)
    create_character(
        state,
        archetype_id=args.archetype,
        gender=Gender(args.gender),
        stats=stats,
    )
    rng = SeededRng(args.seed)
    record = Path(args.record) if args.record else Path(".game_traces") / f"{args.name}.json"
    package = {
        "seed": args.seed,
        "mock_llm": bool(args.mock_llm),
        "record_path": str(record),
        "state": state.model_dump(mode="json"),
        "records": [],
        "rng_state": rng.snapshot(),
    }
    _save_session(args.name, package)
    write_recording(
        record,
        args.seed,
        state,
        [],
        llm_mode=_llm_mode(args.mock_llm),
        mode=TraceMode.MANUAL,
        persona="manual-subagent",
    )
    print(f"session started: {args.name}")
    print(f"trace: {record}")
    _print_current(state)
    return 0


def _resume(args: argparse.Namespace) -> int:
    state, records, seed, rng_state = load_checkpoint(args.from_checkpoint)
    rng = SeededRng.from_snapshot(seed, rng_state) if rng_state is not None else SeededRng(seed)
    record = Path(args.record) if args.record else Path(".game_traces") / f"{args.name}.json"
    package = {
        "seed": seed,
        "mock_llm": bool(args.mock_llm),
        "record_path": str(record),
        "source_checkpoint": str(args.from_checkpoint),
        "state": state.model_dump(mode="json"),
        "records": records,
        "rng_state": rng.snapshot(),
    }
    _save_session(args.name, package)
    write_recording(
        record,
        seed,
        state,
        records,
        llm_mode=_llm_mode(args.mock_llm),
        mode=TraceMode.MANUAL,
        persona="manual-subagent",
    )
    print(f"session resumed: {args.name}")
    print(f"checkpoint: {args.from_checkpoint}")
    print(f"trace: {record}")
    _print_current(state)
    return 0


def _show(args: argparse.Namespace) -> int:
    package = _load_session(args.name)
    state = GameState.model_validate(package["state"])
    _print_current(state)
    return 0


def _choose(args: argparse.Namespace) -> int:
    package = _load_session(args.name)
    state = GameState.model_validate(package["state"])
    records = [record for record in package.get("records", []) if isinstance(record, dict)]
    actions = available_actions(state)
    if args.action < 1 or args.action > len(actions):
        print(f"action index out of range: {args.action}")
        _print_current(state)
        return 2
    action = actions[args.action - 1].action
    if action.kind is ActionKind.START_CONVERSATION and action.target_id is not None:
        resolved = _resolve_intent_action(state, action.target_id, args.intent)
        if resolved is None:
            return 2
        action = resolved

    rng = SeededRng.from_snapshot(int(package["seed"]), _rng_snapshot(package.get("rng_state")))
    input_hash = state_hash(state_hash_payload(state))
    turn = run_turn(
        state,
        action,
        rng,
        heartbreaker_voice=None if package.get("mock_llm") else OpenAIHeartbreakerVoice().generate,
        contextual_options=None if package.get("mock_llm") else ContextualOptionsAgent().generate,
        event_narrator=None if package.get("mock_llm") else OpenAIEventNarrator().narrate,
        conversation_curator=None if package.get("mock_llm") else OpenAIConversationCurator().curate,
        resort_orchestrator=None if package.get("mock_llm") else OpenAIResortOrchestrator().decide,
        background_dialogue=None if package.get("mock_llm") else OpenAIBackgroundDialogue().generate,
    )
    state = turn.state
    records.append(record_from_turn(input_hash, action, turn))
    package["state"] = state.model_dump(mode="json")
    package["records"] = records
    package["rng_state"] = rng.snapshot()
    _save_session(args.name, package)
    write_recording(
        Path(str(package["record_path"])),
        int(package["seed"]),
        state,
        records,
        llm_mode=_llm_mode(bool(package.get("mock_llm"))),
        mode=TraceMode.MANUAL,
        persona="manual-subagent",
    )
    if state.is_terminal:
        print_turn(turn)
        print("session terminal")
    else:
        # Print state first, then the turn result and action menu underneath
        # so the freshest text on the player's screen is "what just happened
        # in the scene" and the menu — not the big stat dump.
        print_state(state)
        print("\n--- this turn ---")
        print_turn(turn)
        print()
        print_actions(available_actions(state))
    return 0


def _checkpoint(args: argparse.Namespace) -> int:
    package = _load_session(args.name)
    state = GameState.model_validate(package["state"])
    records = [record for record in package.get("records", []) if isinstance(record, dict)]
    path = save_named_checkpoint(
        state,
        args.checkpoint,
        records,
        seed=int(package["seed"]),
        rng_state=_rng_snapshot(package.get("rng_state")),
    )
    print(f"checkpoint saved: {path}")
    return 0


def _print_current(state: GameState) -> None:
    print_state(state)
    print_actions(available_actions(state))


def _resolve_intent_action(state: GameState, target_id: str, index: int | None) -> PlayerAction | None:
    intents = available_intents_for(state, target_id)
    numbered: list[tuple[int, str]] = []
    next_index = 1
    for category in IntentCategory:
        category_intents = [intent for intent in intents if intent.category is category]
        print(f"{category.value.title()}:")
        if not category_intents:
            print("  locked")
            continue
        for intent in category_intents:
            print(f"  {next_index}. {intent.label} ({intent.stat_used})")
            numbered.append((next_index, intent.id))
            next_index += 1
    if index is None:
        print("rerun choose with --intent <number>")
        return None
    selected = dict(numbered).get(index)
    if selected is None:
        print(f"intent index out of range: {index}")
        return None
    return PlayerAction(kind=ActionKind.START_CONVERSATION, target_id=target_id, intent_id=selected)


def _parse_stats(raw: str | None, archetype: str) -> PlayerStats:
    if raw is None:
        return DEFAULT_ARCHETYPE_STATS[archetype]
    values = [int(part.strip()) for part in raw.split(",") if part.strip()]
    if len(values) != 5:
        raise ValueError("--stats must provide charm,banter,eq,spark,loyalty")
    return PlayerStats(
        charm=values[0],
        banter=values[1],
        eq=values[2],
        spark=values[3],
        loyalty=values[4],
    )


def _session_path(name: str) -> Path:
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in name)
    return SESSION_DIR / f"{safe.strip('-') or 'session'}.json"


def _load_session(name: str) -> dict[str, Any]:
    path = _session_path(name)
    if not path.exists():
        raise FileNotFoundError(f"session not found: {name}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"session file is invalid: {path}")
    return payload


def _save_session(name: str, package: dict[str, Any]) -> None:
    path = _session_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(package, indent=2), encoding="utf-8")


def _rng_snapshot(payload: object) -> list[object]:
    if not isinstance(payload, list):
        raise ValueError("session is missing JSON RNG state")
    return list(payload)


def _llm_mode(mock_llm: bool) -> str:
    return "mock" if mock_llm else "real"
