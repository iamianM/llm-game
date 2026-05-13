"""Branch comparison report command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.game.reporting.html import table_page
from src.game.state.snapshot import load_checkpoint


def compare_cmd(args: object) -> int:
    """Render a side-by-side branch comparison."""
    checkpoint = args.checkpoint
    trace_a = args.trace_a
    trace_b = args.trace_b
    out = args.out
    _state, checkpoint_records, _seed = load_checkpoint(checkpoint)
    records_a = _load_records(Path(trace_a))
    records_b = _load_records(Path(trace_b))
    rows = _compare_rows(len(checkpoint_records), records_a, records_b)
    Path(out).write_text(
        table_page("Branch Compare", ["Turn", "Branch A", "Branch B"], rows),
        encoding="utf-8",
    )
    return 0


def _load_records(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    records = raw.get("records") if isinstance(raw, dict) else raw
    if not isinstance(records, list):
        raise ValueError(f"trace missing records: {path}")
    return [record for record in records if isinstance(record, dict)]


def _compare_rows(
    fork_turn_count: int,
    records_a: list[dict[str, Any]],
    records_b: list[dict[str, Any]],
) -> list[list[str]]:
    rows: list[list[str]] = []
    for index in range(fork_turn_count, max(len(records_a), len(records_b))):
        a = records_a[index] if index < len(records_a) else None
        b = records_b[index] if index < len(records_b) else None
        rows.append([str(index + 1), _action_summary(a), _action_summary(b)])
    return rows or [["-", "No divergence after checkpoint.", "No divergence after checkpoint."]]


def _action_summary(record: dict[str, Any] | None) -> str:
    if record is None:
        return "-"
    action = record.get("action") or record.get("mechanical_result", {}).get("action", {})
    if not isinstance(action, dict):
        return "unknown"
    return " ".join(
        str(piece)
        for piece in (action.get("kind"), action.get("target_id"), action.get("intent_id"))
        if piece
    )
