"""Fixture verification command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.game.engine.scenario import assert_expected_hash, load_action_script, run_action_script
from src.game.eval.playthrough import evaluate_trace_file


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the verify command."""
    parser = subparsers.add_parser("verify", help="verify deterministic fixtures")
    parser.add_argument("--all", action="store_true", help="verify every fixture")
    parser.add_argument("--fixture", help="single fixture to verify")
    parser.add_argument("--playthrough", help="recorded playthrough trace package to evaluate")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Verify deterministic scenario fixtures."""
    if args.playthrough:
        return _run_playthrough_eval(Path(args.playthrough))
    if args.fixture:
        fixtures = [Path(args.fixture)]
    elif args.all:
        fixture_root = Path("tests/scenarios/fixtures")
        fixtures = sorted(fixture_root.glob("*.yaml")) if fixture_root.is_dir() else []
    else:
        print("choose --all or --fixture", file=sys.stderr)
        return 2

    if not fixtures:
        print("no scenario fixtures to verify", file=sys.stderr)
        return 2

    failures: list[str] = []
    for fixture in fixtures:
        try:
            result = run_action_script(load_action_script(fixture))
            assert_expected_hash(result)
            print(f"ok {fixture}: {result.final_hash}")
        except (AssertionError, FileNotFoundError, ValueError) as exc:
            failures.append(f"{fixture}: {exc}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 2
    return 0


def _run_playthrough_eval(path: Path) -> int:
    report = evaluate_trace_file(path)
    print(report.model_dump_json(indent=2))
    return 0 if report.failed == 0 else 1
