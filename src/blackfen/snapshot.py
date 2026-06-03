"""Checkpoint persistence for Blackfen Road runs."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from src.blackfen.hash import state_hash
from src.blackfen.models import GameState
from src.blackfen.rng import SeededRng

SNAPSHOT_SCHEMA_VERSION = 1
DEFAULT_SAVE_DIR = Path(".blackfen_saves") / "named"
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class BlackfenSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_schema_version: int = SNAPSHOT_SCHEMA_VERSION
    game_id: str = "blackfen_road"
    name: str
    branch_name: str | None = None
    state_hash: str
    rng_state: list[object]
    state: GameState


def save_checkpoint(
    state: GameState,
    rng: SeededRng,
    name: str,
    *,
    branch_name: str | None = None,
    root: Path = DEFAULT_SAVE_DIR,
) -> Path:
    """Write a named checkpoint and return its path."""
    if not _SAFE_NAME.fullmatch(name):
        raise ValueError("checkpoint name must be 1-64 letters, numbers, dots, underscores, or hyphens")
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{name}.json"
    package = BlackfenSnapshot(name=name, branch_name=branch_name, state_hash=state_hash(state), rng_state=rng.snapshot(), state=state)
    path.write_text(json.dumps(package.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_checkpoint(path: Path) -> tuple[GameState, SeededRng, BlackfenSnapshot]:
    """Load a checkpoint package and hydrate state plus RNG."""
    package = BlackfenSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
    if package.state_hash != state_hash(package.state):
        raise ValueError(f"checkpoint hash mismatch: {path}")
    return package.state, SeededRng.from_snapshot(package.state.seed, package.rng_state), package


def resolve_checkpoint_path(value: str, *, root: Path = DEFAULT_SAVE_DIR) -> Path:
    """Resolve either an explicit file path or a default checkpoint name."""
    candidate = Path(value)
    if candidate.is_file():
        return candidate
    named = root / f"{value}.json"
    if named.is_file():
        return named
    raise FileNotFoundError(f"checkpoint not found: {value}")
