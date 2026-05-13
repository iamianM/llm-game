"""CLI report command tests."""

from __future__ import annotations

import json
from types import SimpleNamespace

from src.game.cli.commands.report import packet_cmd


def test_packet_preserves_autopilot_mode_in_eval_dashboard(tmp_path) -> None:
    """Autopilot packet dashboards must not be evaluated as manual traces."""
    trace = tmp_path / "trace.json"
    out = tmp_path / "packet"
    trace.write_text(
        json.dumps(
            {
                "mode": "autopilot",
                "persona": "loyal",
                "llm_mode": "real",
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
    assert "FAIL - Autopilot run reached a terminal outcome" in html
    assert "mode: autopilot; outcome: none" in html
