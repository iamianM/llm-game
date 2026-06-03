"""Verify one Blackfen Road action script."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.blackfen.scenario import assert_expected_hash, load_action_script, run_action_script


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("verify-script", help="verify a Blackfen action script")
    parser.add_argument("--actions", required=True)
    parser.add_argument("--seed", type=int)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    script = load_action_script(Path(args.actions))
    result = run_action_script(script, seed_override=args.seed)
    if args.seed is None:
        assert_expected_hash(result)
    print(f"{script.name}: {result.final_hash}")
    return 0
