"""Snapshot save/load and state hashing.

Design sources:
- docs/qa-strategy.md: Snapshot Contract
- docs/decisions/0008-snapshot-and-trace-architecture.md

Snapshots are the shared restart point for CLI, browser, and tests.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

JsonValue = dict[str, object] | list[object] | str | int | float | bool | None


def state_hash(payload: JsonValue) -> str:
    """Return a stable hash for a JSON-serializable state payload."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def save_snapshot(path: Path, payload: dict[str, object]) -> None:
    """Write a snapshot payload.

    Placeholder JSON implementation until the SQLite snapshot store is built.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_snapshot(path: Path) -> dict[str, object]:
    """Load a snapshot payload."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"snapshot {path} did not contain a JSON object")
    return payload
