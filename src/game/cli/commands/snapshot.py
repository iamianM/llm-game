"""Snapshot command group."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.game.state.snapshot import load_snapshot, state_hash


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the snapshot command group."""
    parser = subparsers.add_parser("snapshot", help="snapshot utilities")
    nested = parser.add_subparsers(dest="snapshot_cmd", required=True)

    inspect = nested.add_parser("inspect", help="inspect a snapshot file")
    inspect.add_argument("file")
    inspect.set_defaults(func=inspect_snapshot_cmd)

    hash_parser = nested.add_parser("hash", help="print a snapshot hash")
    hash_parser.add_argument("file")
    hash_parser.set_defaults(func=hash_snapshot_cmd)

def inspect_snapshot_cmd(args: argparse.Namespace) -> int:
    """Print a snapshot payload."""
    print(load_snapshot(Path(args.file)))
    return 0


def hash_snapshot_cmd(args: argparse.Namespace) -> int:
    """Print the stable hash for a snapshot payload."""
    print(state_hash(load_snapshot(Path(args.file))))
    return 0
