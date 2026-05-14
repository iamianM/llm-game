"""CLI report command tests."""

from __future__ import annotations

import json
from types import SimpleNamespace

from src.game.cli.commands.report import packet_cmd


def test_packet_writes_eval_dashboard_for_manual_trace(tmp_path) -> None:
    trace = tmp_path / "trace.json"
    out = tmp_path / "packet"
    trace.write_text(
        json.dumps(
            {
                "mode": "manual",
                "persona": "",
                "llm_mode": "mock",
                "final_hash": "abc123",
                "records": [],
                "final_state": {"day": 1, "outcome": None},
            }
        ),
        encoding="utf-8",
    )

    result = packet_cmd(SimpleNamespace(trace=str(trace), out=str(out), minimal=True))

    assert result == 0
    html = (out / "playthrough-eval.html").read_text(encoding="utf-8")
    assert "Playthrough Eval" in html
    assert "Autopilot" not in html
