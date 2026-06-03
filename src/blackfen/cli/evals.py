"""Blackfen Road eval CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.blackfen.evals import run_eval_suite


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("eval", help="run Blackfen golden eval scenarios")
    parser.add_argument("--scenarios", default="evals/blackfen/scenarios")
    parser.add_argument("--out", default="review-packet/blackfen-eval")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    results = run_eval_suite(scenario_dir=Path(args.scenarios), out_dir=Path(args.out))
    failures = [result for result in results if not result.passed]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}: hash={result.final_hash} status={result.final_status.value} fun={result.fun_score}/100")
    return 1 if failures else 0
