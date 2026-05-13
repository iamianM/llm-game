"""Reviewer note commands for trace packets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.game.state.bookmarks import Bookmark


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register review note commands."""
    parser = subparsers.add_parser("review", help="manage reviewer notes")
    nested = parser.add_subparsers(dest="review_cmd", required=True)
    notes = nested.add_parser("notes", help="manage review note bookmarks")
    note_cmd = notes.add_subparsers(dest="notes_cmd", required=True)

    add = note_cmd.add_parser("add", help="add one reviewer bookmark")
    add.add_argument("--trace", required=True)
    add.add_argument("--turn", type=int, required=True)
    add.add_argument("--category", choices=["highlight", "anomaly", "regression", "smell", "note"], required=True)
    add.add_argument("--title", required=True)
    add.add_argument("--note", required=True)
    add.set_defaults(func=add_note_cmd)

    list_cmd = note_cmd.add_parser("list", help="list reviewer bookmarks")
    list_cmd.add_argument("--trace", required=True)
    list_cmd.set_defaults(func=list_notes_cmd)

    clear = note_cmd.add_parser("clear", help="clear reviewer bookmarks")
    clear.add_argument("--trace", required=True)
    clear.set_defaults(func=clear_notes_cmd)


def add_note_cmd(args: argparse.Namespace) -> int:
    path = _notes_path(Path(args.trace))
    notes = _read_notes(path)
    category = "note" if args.category in {"regression", "smell"} else args.category
    notes.append(
        Bookmark(
            turn=args.turn,
            kind=f"review_{args.category}",
            category=category,
            title=args.title,
            note=args.note,
        ).model_dump(mode="json")
    )
    _write_notes(path, notes)
    print(path)
    return 0


def list_notes_cmd(args: argparse.Namespace) -> int:
    for note in _read_notes(_notes_path(Path(args.trace))):
        print(f"turn {note.get('turn')}: {note.get('category')} - {note.get('title')}")
    return 0


def clear_notes_cmd(args: argparse.Namespace) -> int:
    _write_notes(_notes_path(Path(args.trace)), [])
    return 0


def review_notes_for_trace(trace_path: Path) -> list[dict[str, object]]:
    """Return reviewer-authored notes for a trace, if any."""
    return _read_notes(_notes_path(trace_path))


def _notes_path(trace_path: Path) -> Path:
    return trace_path.with_name(f"{trace_path.stem}-review-notes.json")


def _read_notes(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"review notes must be a list: {path}")
    return [note for note in raw if isinstance(note, dict)]


def _write_notes(path: Path, notes: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(notes, indent=2), encoding="utf-8")
