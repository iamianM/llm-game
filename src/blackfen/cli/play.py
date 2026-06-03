"""Interactive Blackfen Road CLI play."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.blackfen.agents.intent import LocalIntentParser
from src.blackfen.agents.narrator import MockNarrator
from src.blackfen.content import load_world
from src.blackfen.engine import run_turn
from src.blackfen.hash import state_hash
from src.blackfen.models import GameState, RunStatus
from src.blackfen.new_game import new_game
from src.blackfen.rng import SeededRng
from src.blackfen.snapshot import load_checkpoint, resolve_checkpoint_path, save_checkpoint
from src.blackfen.trace import build_trace_from_state, load_trace, replay_trace, save_trace


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("play", help="play Blackfen Road in the terminal")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--name", default="You")
    parser.add_argument("--class-id", choices=["fighter", "rogue", "mage"], default="fighter")
    parser.add_argument("--from-checkpoint", help="resume from a checkpoint name or path")
    parser.add_argument("--branch-name", help="label checkpoints created from this run")
    parser.add_argument("--record", nargs="?", const="", help="record the session to a trace path or .blackfen_traces")
    parser.add_argument("--replay", help="replay a saved trace package instead of starting interactive play")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    if args.replay:
        package = load_trace(Path(args.replay))
        result = replay_trace(package)
        for turn in result.turns:
            print(f"> {turn.raw_text}")
            print(turn.narration)
            print(f"hash {turn.output_hash}")
        print(f"Replay verified: {result.final_hash}")
        return 0
    if args.from_checkpoint:
        state, rng, checkpoint = load_checkpoint(resolve_checkpoint_path(args.from_checkpoint))
        print(f"Resumed checkpoint {checkpoint.name}: {checkpoint.state_hash}")
    else:
        state = new_game(args.seed, player_name=args.name, class_id=args.class_id)
        rng = SeededRng(args.seed)
    parser = LocalIntentParser()
    narrator = MockNarrator()
    print(_render_state(state))
    while state.status is RunStatus.ACTIVE:
        try:
            raw = input("> ").strip()
        except EOFError:
            print()
            break
        if raw in {"/quit", "quit", "exit"}:
            break
        if raw == "/help":
            print("Commands: freeform action, /state, /hash, /checkpoint <name>, /help, /quit")
            continue
        if raw == "/state":
            print(_render_state(state))
            continue
        if raw == "/hash":
            print(state_hash(state))
            continue
        if raw.startswith("/checkpoint "):
            name = raw.removeprefix("/checkpoint ").strip()
            try:
                path = save_checkpoint(state, rng, name, branch_name=args.branch_name)
            except ValueError as exc:
                print(f"Invalid checkpoint: {exc}")
                continue
            print(f"Checkpoint saved: {path}")
            continue
        try:
            turn = run_turn(state, raw, rng, parser=parser, narrator=narrator)
        except ValueError as exc:
            print(f"Invalid action: {exc}")
            continue
        print(turn.narration)
        print(_status_line(state))
    if state.status is not RunStatus.ACTIVE:
            print(f"Run ended: {state.status.value}. Hash: {state_hash(state)}")
    if args.record is not None and state.turns:
        trace_path = Path(args.record) if args.record else None
        saved = save_trace(build_trace_from_state(state, name=f"interactive-{state.seed}"), trace_path)
        print(f"Trace recorded: {saved}")
    return 0


def _render_state(state: GameState) -> str:
    world = load_world()
    location = world.locations[state.current_location_id]
    known = ", ".join(world.locations[id_].name for id_ in state.known_locations)
    npcs = ", ".join(world.npcs[id_].name for id_ in location.npcs) or "none"
    return "\n".join([
        "Blackfen Road",
        _status_line(state),
        f"Location: {location.name}",
        location.description,
        f"People here: {npcs}",
        f"Known places: {known}",
        "Commands: freeform action, /state, /hash, /checkpoint <name>, /help, /quit",
    ])


def _status_line(state: GameState) -> str:
    return f"{state.player.name} HP {state.player.hp}/{state.player.max_hp} | Elian HP {state.companion.hp}/{state.companion.max_hp} | Turn {state.turn_index}"
