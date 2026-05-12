"""Scenario command group."""

from __future__ import annotations

import argparse


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the scenario command group."""
    parser = subparsers.add_parser("scenario", help="scenario utilities")
    nested = parser.add_subparsers(dest="scenario_cmd", required=True)

    run_parser = nested.add_parser("run", help="run one scenario file")
    run_parser.add_argument("file")
    run_parser.set_defaults(func=run_cmd)


def run_cmd(args: argparse.Namespace) -> int:
    """Run a scenario placeholder."""
    print(f"scenario run is scaffolded: {args.file}")
    return 0
