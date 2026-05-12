"""Balance simulation command."""

from __future__ import annotations

import argparse


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the simulate command."""
    parser = subparsers.add_parser("simulate", help="run deterministic balance simulations")
    parser.add_argument("--seeds", type=int, default=1000)
    parser.add_argument("--actions", choices=("random", "policy"), default="random")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Run simulation placeholder."""
    print(f"simulate command is scaffolded: seeds={args.seeds} actions={args.actions}")
    return 0
