"""Verify checked-in Blackfen Road scenario fixtures."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.blackfen.scenario import assert_expected_hash, load_action_script, run_action_script

FIXTURE_DIR = Path("tests") / "blackfen" / "fixtures"


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("verify", help="verify Blackfen scenario fixtures")
    parser.add_argument("--all", action="store_true", required=True)
    parser.set_defaults(func=run)


def run(_args: argparse.Namespace) -> int:
    paths = sorted(FIXTURE_DIR.glob("*.yaml"))
    if not paths:
        raise FileNotFoundError(f"no Blackfen fixtures found in {FIXTURE_DIR}")
    for path in paths:
        result = run_action_script(load_action_script(path))
        assert_expected_hash(result)
        print(f"{path}: {result.final_hash}")
    return 0
