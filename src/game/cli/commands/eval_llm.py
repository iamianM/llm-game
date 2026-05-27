"""Golden LLM eval command."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.game.eval.golden_runner import load_golden_scenarios, run_golden_eval


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the llm-eval command."""
    parser = subparsers.add_parser("llm-eval", help="run authored golden LLM eval scenarios")
    parser.add_argument(
        "--scenarios",
        default="evals/llm/scenarios",
        help="scenario YAML file or directory",
    )
    parser.add_argument("--out", default="review-packet/llm-eval", help="output report directory")
    parser.add_argument("--real-llm", action="store_true", help="use live OpenAI agents")
    parser.add_argument("--judge", action="store_true", help="run optional LLM judge checks")
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="parallel scenario workers (default: min(scenarios, 8); pass 1 to disable)",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Run golden LLM eval scenarios."""
    scenarios = load_golden_scenarios(Path(args.scenarios))
    result = run_golden_eval(
        scenarios,
        out=Path(args.out),
        real_llm=bool(args.real_llm),
        judge=bool(args.judge),
        max_workers=args.max_workers,
    )
    print(f"golden eval report: {Path(args.out) / 'index.html'}")
    print(
        f"scenarios={result.scenario_count} workers={result.worker_count} pass={result.passed} "
        f"fail={result.failed} cannot_determine={result.cannot_determine}"
    )
    return 0 if result.failed == 0 else 1
