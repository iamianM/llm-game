"""Fixture verification command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the verify command."""
    parser = subparsers.add_parser("verify", help="verify deterministic fixtures")
    parser.add_argument("--all", action="store_true", help="verify every fixture")
    parser.add_argument("--fixture", help="single fixture to verify")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Run deterministic fixture verification placeholder."""
    if args.fixture:
        if not Path(args.fixture).is_file():
            print(f"fixture not found: {args.fixture}", file=sys.stderr)
            return 2
        print(f"verify command is scaffolded: {args.fixture}")
        return 0
    if args.all:
        fixture_root = Path("tests/scenarios/fixtures")
        fixtures = sorted(fixture_root.glob("*.yaml")) if fixture_root.is_dir() else []
        if not fixtures:
            print("no scenario fixtures to verify yet", file=sys.stderr)
            return 2
        print(f"verify command is scaffolded: {len(fixtures)} fixture(s)")
        return 0
    print("choose --all or --fixture", file=sys.stderr)
    return 2
