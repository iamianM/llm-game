"""Content command group."""

from __future__ import annotations

import argparse

from src.game.content.lint import run_lint


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the content command group."""
    parser = subparsers.add_parser("content", help="content utilities")
    nested = parser.add_subparsers(dest="content_cmd", required=True)

    lint = nested.add_parser("lint", help="validate runtime content")
    lint.set_defaults(func=lint_cmd)


def lint_cmd(args: argparse.Namespace) -> int:
    """Run content lint."""
    del args
    run_lint()
    return 0
