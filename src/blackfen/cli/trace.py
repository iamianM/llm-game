"""Blackfen Road trace inspection and replay commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.blackfen.trace import load_trace, replay_trace


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("trace", help="inspect or replay Blackfen trace packages")
    trace_subparsers = parser.add_subparsers(dest="trace_command", required=True)

    inspect_parser = trace_subparsers.add_parser("inspect", help="show trace metadata")
    inspect_parser.add_argument("path")
    inspect_parser.set_defaults(func=inspect_trace)

    replay_parser = trace_subparsers.add_parser("replay", help="verify a trace by deterministic replay")
    replay_parser.add_argument("path")
    replay_parser.set_defaults(func=replay)


def inspect_trace(args: argparse.Namespace) -> int:
    package = load_trace(Path(args.path))
    print(f"{package.name}: seed={package.seed} turns={len(package.turns)} status={package.final_state.status.value} hash={package.final_hash} fun={package.fun_score}/100")
    for note in package.review_notes:
        print(f"- {note}")
    return 0


def replay(args: argparse.Namespace) -> int:
    result = replay_trace(load_trace(Path(args.path)))
    print(f"Replay verified: {result.final_hash}")
    return 0
