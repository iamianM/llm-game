"""Static HTML report generation."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from src.game.cli.commands.report_compare import compare_cmd
from src.game.cli.commands.review import review_notes_for_trace
from src.game.eval.playthrough import evaluate_trace
from src.game.reporting.balance import run_balance
from src.game.reporting.eval_dashboard import playthrough_eval_page
from src.game.reporting.html import index_page, session_page, session_page_minimal, table_page
from src.game.reporting.packet_text import infer_llm_mode, llm_mode_note, notes, repro


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the report command group."""
    parser = subparsers.add_parser("report", help="generate static review reports")
    nested = parser.add_subparsers(dest="report_cmd", required=True)

    session = nested.add_parser("session", help="render one trace JSON file")
    session.add_argument("trace_path")
    session.add_argument("--out", required=True)
    session.add_argument("--minimal", action="store_true")
    session.set_defaults(func=session_cmd)

    from_trace = nested.add_parser("from-trace", help="render one recorded playthrough trace")
    from_trace.add_argument("trace_path")
    from_trace.add_argument("--out", required=True)
    from_trace.add_argument("--minimal", action="store_true")
    from_trace.set_defaults(func=session_cmd)

    balance = nested.add_parser("balance", help="render balance simulation")
    balance.add_argument("--seeds", type=int, default=1000)
    balance.add_argument("--out", required=True)
    balance.set_defaults(func=balance_cmd)

    packet = nested.add_parser("packet", help="build the full review packet")
    packet.add_argument("--trace", required=True)
    packet.add_argument("--out", default="review-packet")
    packet.add_argument("--minimal", action="store_true")
    packet.set_defaults(func=packet_cmd)

    eval_dashboard = nested.add_parser(
        "eval-dashboard", help="render playthrough eval dashboard"
    )
    eval_dashboard.add_argument("trace_path")
    eval_dashboard.add_argument("--out", required=True)
    eval_dashboard.set_defaults(func=eval_dashboard_cmd)

    compare = nested.add_parser("compare", help="compare two checkpoint branches")
    compare.add_argument("--checkpoint", required=True)
    compare.add_argument("--trace-a", required=True)
    compare.add_argument("--trace-b", required=True)
    compare.add_argument("--out", required=True)
    compare.set_defaults(func=compare_cmd)


def session_cmd(args: argparse.Namespace) -> int:
    """Render one existing trace file."""
    records, final_state, _final_hash, llm_mode, mode, persona = _load_recording(
        Path(args.trace_path)
    )
    preface = (
        _final_state_summary(final_state, llm_mode, mode, persona)
        if final_state is not None
        else ""
    )
    minimal = getattr(args, "minimal", False)
    if minimal:
        html = session_page_minimal(Path(args.trace_path).stem, records, preface=preface)
    else:
        html = session_page(
            Path(args.trace_path).stem,
            records,
            preface=preface,
            final_state=final_state,
        )
    Path(args.out).write_text(html, encoding="utf-8")
    return 0


def balance_cmd(args: argparse.Namespace) -> int:
    """Render balance reports."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    outcomes, actions = run_balance(
        args.seeds, Path("tests/scenarios/fixtures/day6-full-run.yaml")
    )
    _write_balance_pages(out, outcomes, actions)
    return 0


def packet_cmd(args: argparse.Namespace) -> int:
    """Build a single-session review packet from a recorded trace."""
    trace_path = Path(args.trace)
    records, final_state, final_hash, llm_mode, mode, persona = _load_recording(trace_path)
    if final_state is None:
        raise ValueError("packet requires a recorded trace package with final_state")
    out = Path(args.out)
    _clean_packet_output(out)
    (out / "artifacts").mkdir(parents=True, exist_ok=True)
    report = evaluate_trace(
        {
            "records": records,
            "final_state": final_state,
            "final_hash": final_hash,
            "mode": mode,
            "persona": persona,
        },
        trace_path=str(trace_path),
    )
    (out / "session.html").write_text(
        session_page(
            "Recorded Playthrough",
            records,
            preface=_final_state_summary(final_state, llm_mode, mode, persona),
            reviewer_notes=review_notes_for_trace(trace_path),
            final_state=final_state,
        ),
        encoding="utf-8",
    )
    (out / "playthrough-eval.html").write_text(
        playthrough_eval_page(report),
        encoding="utf-8",
    )
    (out / "artifacts" / "session.json").write_text(
        json.dumps(final_state, indent=2),
        encoding="utf-8",
    )
    (out / "artifacts" / "session-trace.json").write_text(
        json.dumps(records, indent=2),
        encoding="utf-8",
    )
    (out / "notes.md").write_text(notes(records, final_hash, llm_mode), encoding="utf-8")
    (out / "how-to-reproduce.md").write_text(repro(trace_path, out), encoding="utf-8")
    links = [
        ("Recorded playthrough", "session.html"),
        ("Playthrough eval dashboard", "playthrough-eval.html"),
        ("Final state JSON", "artifacts/session.json"),
        ("Trace JSON", "artifacts/session-trace.json"),
        ("Notes", "notes.md"),
        ("How to reproduce", "how-to-reproduce.md"),
    ]
    (out / "index.html").write_text(index_page(links), encoding="utf-8")
    return 0


def eval_dashboard_cmd(args: argparse.Namespace) -> int:
    """Render only the playthrough eval dashboard for one trace."""
    records, final_state, final_hash, _llm_mode, mode, persona = _load_recording(
        Path(args.trace_path)
    )
    report = evaluate_trace(
        {
            "records": records,
            "final_state": final_state,
            "final_hash": final_hash,
            "mode": mode,
            "persona": persona,
        },
        trace_path=args.trace_path,
    )
    Path(args.out).write_text(playthrough_eval_page(report), encoding="utf-8")
    return 0


def _write_balance_pages(out: Path, outcomes: object, actions: object) -> None:
    out.mkdir(parents=True, exist_ok=True)
    outcome_rows = [[str(key), str(value)] for key, value in sorted(outcomes.items())]
    action_rows = [[str(key), str(value)] for key, value in sorted(actions.items())]
    (out / "distribution.html").write_text(
        table_page("Balance Distribution", ["Outcome", "Count"], outcome_rows),
        encoding="utf-8",
    )
    (out / "action-coverage.html").write_text(
        table_page("Action Coverage", ["Action", "Count"], action_rows),
        encoding="utf-8",
    )


def _load_recording(
    path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, str | None, str, str, str | None]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw, None, None, infer_llm_mode(raw), "manual", None
    if not isinstance(raw, dict):
        raise ValueError(f"recording must be a JSON object or list: {path}")
    records = raw.get("records")
    if not isinstance(records, list):
        raise ValueError(f"recording is missing records list: {path}")
    final_state = raw.get("final_state")
    if final_state is not None and not isinstance(final_state, dict):
        raise ValueError(f"recording final_state must be an object: {path}")
    final_hash = raw.get("final_hash")
    if final_hash is not None and not isinstance(final_hash, str):
        raise ValueError(f"recording final_hash must be a string: {path}")
    llm_mode = raw.get("llm_mode")
    if not isinstance(llm_mode, str):
        llm_mode = infer_llm_mode(records)
    mode = raw.get("mode")
    if not isinstance(mode, str):
        mode = "manual"
    persona = raw.get("persona")
    if not isinstance(persona, str):
        persona = None
    return records, final_state, final_hash, llm_mode, mode, persona


def _clean_packet_output(out: Path) -> None:
    for directory in ("artifacts", "sessions", "balance", "narration-quality"):
        shutil.rmtree(out / directory, ignore_errors=True)
    for file_name in (
        "index.html",
        "session.html",
        "playthrough-eval.html",
        "notes.md",
        "how-to-reproduce.md",
    ):
        (out / file_name).unlink(missing_ok=True)


def _final_state_summary(
    final_state: dict[str, Any],
    llm_mode: str,
    mode: str,
    persona: str | None,
) -> str:
    player = final_state.get("player")
    heartbreakers = final_state.get("heartbreakers")
    memory_lines: list[str] = []
    if isinstance(player, dict):
        memories = player.get("memories")
        if isinstance(memories, list):
            memory_lines.append(f"<li>Player memories: {len(memories)}</li>")
        outcome = final_state.get("outcome")
        if isinstance(outcome, str):
            memory_lines.append(f"<li>Final outcome: {outcome}</li>")
    if isinstance(heartbreakers, list):
        for heartbreaker in heartbreakers:
            if not isinstance(heartbreaker, dict):
                continue
            memories = heartbreaker.get("memories")
            name = heartbreaker.get("name", heartbreaker.get("id", "heartbreaker"))
            if isinstance(memories, list):
                memory_lines.append(f"<li>{name} memories: {len(memories)}</li>")
    return (
        "<p><b>Recorded playthrough.</b> This report is rendered from a trace package; "
        "agent commits are replayable and no new LLM calls are needed to inspect it.</p>"
        f"<p><b>LLM mode:</b> {llm_mode}. {llm_mode_note(llm_mode)}</p>"
        f"<p><b>Trace mode:</b> {mode}{f' - persona: {persona}' if persona else ''}.</p>"
        f"<ul>{''.join(memory_lines)}</ul>"
    )
