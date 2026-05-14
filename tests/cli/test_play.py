"""CLI play command rendering tests."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO

from src.game.cli.commands.play_render import print_background_history


def test_cli_background_command_prints_last_three() -> None:
    records = [
        {
            "agent_commits": {
                "background_dialogues": [
                    {
                        "speaker_a_id": f"a{index}",
                        "speaker_b_id": f"b{index}",
                        "speaker_a_line": f"line a {index}",
                        "speaker_b_line": f"line b {index}",
                        "tone": "warm",
                    }
                ]
            }
        }
        for index in range(4)
    ]
    stdout = StringIO()

    with redirect_stdout(stdout):
        print_background_history(records)

    output = stdout.getvalue()
    assert "line a 0" not in output
    assert "line a 1" in output
    assert "line a 3" in output
