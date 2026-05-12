"""Command dispatcher for `python -m src.game.cli`."""

from __future__ import annotations

import argparse
import sys

from src.game.cli.commands import (
    codegen,
    content,
    play,
    replay,
    report,
    scenario,
    simulate,
    snapshot,
    trace,
    verify,
)


def main(argv: list[str] | None = None) -> int:
    """Parse command-line arguments and dispatch to a subcommand."""
    parser = argparse.ArgumentParser(prog="game")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for module in (
        play,
        report,
        replay,
        verify,
        snapshot,
        content,
        scenario,
        trace,
        simulate,
        codegen,
    ):
        module.add_parser(subparsers)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
