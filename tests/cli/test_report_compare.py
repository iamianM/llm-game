"""Tests for branch comparison report command."""

from __future__ import annotations

import argparse
import json

from src.game.cli.commands.report import compare_cmd
from src.game.state.models import new_game
from src.game.state.snapshot import save_named_checkpoint


def test_report_compare_writes_html(tmp_path, monkeypatch) -> None:
    state = new_game(1)
    final_state = state.model_dump(mode="json")
    monkeypatch.chdir(tmp_path)
    save_named_checkpoint(state, "fork", [{"turn": 1}], seed=1)
    trace_a = tmp_path / "a.json"
    trace_b = tmp_path / "b.json"
    _write_trace(trace_a, "start_conversation", final_state)
    _write_trace(trace_b, "advance_phase", final_state)
    out = tmp_path / "compare.html"

    compare_cmd(
        argparse.Namespace(
            checkpoint="fork",
            trace_a=str(trace_a),
            trace_b=str(trace_b),
            out=str(out),
        )
    )

    html = out.read_text(encoding="utf-8")
    assert "Branch Compare" in html
    assert "advance_phase" in html


def _write_trace(path, second_action: str, final_state: dict[str, object]) -> None:
    path.write_text(
        json.dumps(
            {
                "seed": 1,
                "records": [
                    {"turn": 1, "action": {"kind": "advance_phase"}},
                    {"turn": 2, "action": {"kind": second_action}},
                ],
                "final_state": final_state,
                "final_hash": "hash",
            }
        ),
        encoding="utf-8",
    )
