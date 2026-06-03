"""Blackfen content validation CLI."""

from __future__ import annotations

import argparse

from src.blackfen.content import lint_world


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("content", help="Blackfen content tools")
    nested = parser.add_subparsers(dest="content_command", required=True)
    lint = nested.add_parser("lint", help="validate Blackfen world data")
    lint.set_defaults(func=run_lint)


def run_lint(_args: argparse.Namespace) -> int:
    world = lint_world()
    print(f"Blackfen content ok: {len(world.locations)} locations, {len(world.npcs)} NPCs, {len(world.monsters)} monsters")
    return 0
