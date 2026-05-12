"""Snapshot command group."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.game.state.snapshot import load_snapshot, state_hash


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the snapshot command group."""
    parser = subparsers.add_parser("snapshot", help="snapshot utilities")
    nested = parser.add_subparsers(dest="snapshot_cmd", required=True)

    save = nested.add_parser("save", help="save a named snapshot")
    save.add_argument("name")
    save.set_defaults(func=save_snapshot_cmd)

    load = nested.add_parser("load", help="load a named snapshot")
    load.add_argument("name")
    load.set_defaults(func=load_snapshot_cmd)

    inspect = nested.add_parser("inspect", help="inspect a snapshot file")
    inspect.add_argument("file")
    inspect.set_defaults(func=inspect_snapshot_cmd)

    hash_parser = nested.add_parser("hash", help="print a snapshot hash")
    hash_parser.add_argument("file")
    hash_parser.set_defaults(func=hash_snapshot_cmd)


def save_snapshot_cmd(args: argparse.Namespace) -> int:
    """Placeholder for in-session snapshot save."""
    print(f"snapshot save is scaffolded: {args.name}")
    return 0


def load_snapshot_cmd(args: argparse.Namespace) -> int:
    """Placeholder for in-session snapshot load."""
    print(f"snapshot load is scaffolded: {args.name}")
    return 0


def inspect_snapshot_cmd(args: argparse.Namespace) -> int:
    """Print a snapshot payload."""
    print(load_snapshot(Path(args.file)))
    return 0


def hash_snapshot_cmd(args: argparse.Namespace) -> int:
    """Print the stable hash for a snapshot payload."""
    print(state_hash(load_snapshot(Path(args.file))))
    return 0
