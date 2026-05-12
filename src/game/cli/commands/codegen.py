"""Type generation command."""

from __future__ import annotations

import argparse


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the codegen command."""
    parser = subparsers.add_parser("codegen", help="generate browser types from schemas")
    parser.add_argument("--out", required=True)
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Run codegen placeholder."""
    print(f"codegen command is scaffolded: {args.out}")
    return 0
