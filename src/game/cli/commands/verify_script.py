"""Verify-script command for deterministic action scripts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.game.engine.scenario import assert_expected_hash, load_action_script, run_action_script


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the verify-script command."""
    parser = subparsers.add_parser("verify-script", help="verify an action script")
    parser.add_argument("--seed", type=int, required=False)
    parser.add_argument("--actions", required=False, help="YAML action script")
    parser.add_argument("--mock-llm", action="store_true")
    parser.add_argument("--exit-on-end", action="store_true")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Verify a deterministic action script."""
    if not args.actions:
        print("verify-script requires --actions", file=sys.stderr)
        return 2
    try:
        script = load_action_script(Path(args.actions))
        result = run_action_script(script, seed_override=args.seed)
        if result.script.expected_hash is not None:
            assert_expected_hash(result)
    except (AssertionError, FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"script: {result.script.name}")
    print(f"seed: {result.state.seed}")
    print(f"turns: {len(result.turns)}")
    print(f"phase: {result.state.phase.value}")
    print(f"hash: {result.final_hash}")
    return 0
