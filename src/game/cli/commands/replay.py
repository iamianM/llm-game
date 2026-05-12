"""Replay command for deterministic action scripts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the replay command."""
    parser = subparsers.add_parser("replay", help="replay an action script")
    parser.add_argument("--seed", type=int, required=False)
    parser.add_argument("--actions", required=False, help="YAML action script")
    parser.add_argument("--snapshot", help="optional starting snapshot")
    parser.add_argument("--mock-llm", action="store_true")
    parser.add_argument("--exit-on-end", action="store_true")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Run the replay command placeholder."""
    if args.actions and not Path(args.actions).is_file():
        print(f"action script not found: {args.actions}", file=sys.stderr)
        return 2
    print("replay command is scaffolded; implement action-script replay next")
    if args.seed is not None:
        print(f"seed: {args.seed}")
    if args.actions:
        print(f"actions: {args.actions}")
    return 0
