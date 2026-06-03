"""Blackfen Road review packet commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.blackfen.report import write_report_packet


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("report", help="build Blackfen review packets")
    report_subparsers = parser.add_subparsers(dest="report_command", required=True)

    packet = report_subparsers.add_parser("packet", help="write a static HTML packet for a trace")
    packet.add_argument("--trace", required=True)
    packet.add_argument("--out", required=True)
    packet.set_defaults(func=run_packet)


def run_packet(args: argparse.Namespace) -> int:
    report = write_report_packet(Path(args.trace), Path(args.out))
    print(f"Report written: {report}")
    return 0
