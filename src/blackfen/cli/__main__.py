"""Command dispatcher for `python -m src.blackfen.cli`."""

from __future__ import annotations

import argparse
import sys

from src.blackfen.cli import content, play, verify, verify_script


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="blackfen")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for module in (play, verify_script, verify, content):
        module.add_parser(subparsers)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
