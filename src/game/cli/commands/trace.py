"""Trace command group."""

from __future__ import annotations

import argparse
from pathlib import Path


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the trace command group."""
    parser = subparsers.add_parser("trace", help="trace utilities")
    nested = parser.add_subparsers(dest="trace_cmd", required=True)

    inspect = nested.add_parser("inspect", help="inspect a trace file")
    inspect.add_argument("file")
    inspect.set_defaults(func=inspect_cmd)


def inspect_cmd(args: argparse.Namespace) -> int:
    """Print a trace file."""
    print(Path(args.file).read_text(encoding="utf-8"))
    return 0
