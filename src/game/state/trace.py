"""Turn trace writing.

Design sources:
- docs/systems/qa.md: Trace Contract
- docs/decisions/0008-snapshot-and-trace-architecture.md

Traces are the common debugging artifact for users, CLI runs, browser sessions,
and AI assistants.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any


class TraceMode(StrEnum):
    MANUAL = "manual"
    MOCKED = "mocked"


def write_turn_trace(path: Path, payload: dict[str, Any]) -> None:
    """Write one turn trace payload as JSON until the trace store is formalized."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
