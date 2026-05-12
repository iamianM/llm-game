"""Interactive play command."""

from __future__ import annotations

import argparse


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the play command."""
    parser = subparsers.add_parser("play", help="start an interactive CLI game")
    parser.add_argument("--snapshot", help="snapshot to load")
    parser.add_argument("--seed", type=int, help="seed for a new run")
    parser.add_argument("--mock-llm", action="store_true", help="use deterministic mock narration")
    parser.add_argument("--trace", action="store_true", help="write turn traces")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Run the interactive play command placeholder."""
    print("play command is scaffolded; implement deterministic engine loop next")
    if args.snapshot:
        print(f"snapshot: {args.snapshot}")
    if args.seed is not None:
        print(f"seed: {args.seed}")
    return 0
