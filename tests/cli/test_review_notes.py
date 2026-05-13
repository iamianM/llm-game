"""Tests for reviewer note CLI helpers."""

from __future__ import annotations

import argparse

from src.game.cli.commands.review import add_note_cmd, clear_notes_cmd, review_notes_for_trace


def test_review_notes_add_and_clear(tmp_path) -> None:
    trace = tmp_path / "trace.json"
    trace.write_text("{}", encoding="utf-8")

    add_note_cmd(
        argparse.Namespace(
            trace=str(trace),
            turn=3,
            category="highlight",
            title="Good beat",
            note="Worth reviewing.",
        )
    )

    notes = review_notes_for_trace(trace)
    assert notes[0]["turn"] == 3
    assert notes[0]["title"] == "Good beat"

    clear_notes_cmd(argparse.Namespace(trace=str(trace)))

    assert review_notes_for_trace(trace) == []
