"""Checkpoint discovery + load helpers for the API layer.

Surfaces both the bundled `data/checkpoints/*.json` demo set (which ships
with the lambda) and any locally-saved `.game_saves/named/*.json` (which
only exist in the developer's working tree). Both must be at the current
`SCHEMA_VERSION` to be returnable — stale checkpoints are filtered out so
the UI never offers a load that's going to crash.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.game.state.models import SCHEMA_VERSION

# Path to bundled demo checkpoints, resolved relative to this file so it
# works from the Vercel lambda's /var/task cwd as well as the dev shell.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BUNDLED_DIR = _REPO_ROOT / "data" / "checkpoints"
_LOCAL_DIR = _REPO_ROOT / ".game_saves" / "named"


@dataclass(frozen=True)
class CheckpointSummary:
    """Minimal metadata the main-menu UI renders for each option."""

    name: str
    label: str
    day: int
    phase: str
    source: str  # "bundled" or "local"
    file_path: str  # absolute path; used internally by load_named_checkpoint


def list_checkpoints() -> list[CheckpointSummary]:
    """Return every loadable checkpoint at the current schema version.

    Bundled checkpoints come first, then any locally-saved checkpoints
    (development-only). Stale-schema files are silently dropped so the
    user never sees a "load this" button that would 502.
    """
    seen: set[str] = set()
    summaries: list[CheckpointSummary] = []
    for source, directory in (("bundled", _BUNDLED_DIR), ("local", _LOCAL_DIR)):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            summary = _summarize(path, source)
            if summary is None:
                continue
            if summary.name in seen:
                continue
            seen.add(summary.name)
            summaries.append(summary)
    return summaries


def load_named_checkpoint_payload(name: str) -> dict[str, object]:
    """Return the raw JSON payload for ``name`` (bundled or local).

    Returns the same shape `save_named_checkpoint` writes:
    ``{name, seed, state, trace_records, rng_state}``. Raises ``KeyError``
    when the checkpoint doesn't exist or is at the wrong schema version.
    """
    candidates = [
        _BUNDLED_DIR / f"{name}.json",
        _LOCAL_DIR / f"{name}.json",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        state = payload.get("state")
        if not isinstance(state, dict) or state.get("schema_version") != SCHEMA_VERSION:
            continue
        return payload
    raise KeyError(name)


def _summarize(path: Path, source: str) -> CheckpointSummary | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    state = raw.get("state")
    if not isinstance(state, dict):
        return None
    if state.get("schema_version") != SCHEMA_VERSION:
        return None
    day = state.get("day")
    phase = state.get("phase")
    if not isinstance(day, int) or not isinstance(phase, str):
        return None
    return CheckpointSummary(
        name=path.stem,
        label=_humanize(path.stem),
        day=day,
        phase=phase,
        source=source,
        file_path=str(path),
    )


def _humanize(slug: str) -> str:
    import re
    # Split CamelCase, snake_case, kebab-case, AND alpha/digit boundaries —
    # "day1-end-with-chloe" -> "Day 1 End With Chloe", "playtest_bravo_day3"
    # -> "Playtest Bravo Day 3".
    normalized = slug.replace("_", "-")
    spaced = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", normalized)
    spaced = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", spaced)
    parts = [part for part in spaced.split("-") if part]
    return " ".join(part.capitalize() for part in parts)


__all__ = (
    "CheckpointSummary",
    "list_checkpoints",
    "load_named_checkpoint_payload",
)
