"""Deterministic action-script replay.

Design sources:
- docs/qa-strategy.md: L4 Scenario
- docs/decisions/0008-snapshot-and-trace-architecture.md

Scenario replay is shared by CLI commands and pytest so smoke tests, fixture
verification, and manual debugging all exercise the same engine path.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.game.engine.actions import PlayerAction
from src.game.engine.turn import TurnResult, run_turn
from src.game.state.models import GameState, PlayerStats, new_game
from src.game.state.rng import SeededRng
from src.game.state.snapshot import state_hash


class ActionScript(BaseModel):
    """A YAML action script for deterministic replay."""

    model_config = ConfigDict(extra="forbid")

    name: str
    seed: int
    player_stats: PlayerStats | None = None
    actions: list[PlayerAction] = Field(min_length=1)
    expected_hash: str | None = None


class ScenarioRunResult(BaseModel):
    """Replay result used by CLI and tests."""

    model_config = ConfigDict(extra="forbid")

    script: ActionScript
    state: GameState
    turns: list[TurnResult]
    final_hash: str


def load_action_script(path: Path) -> ActionScript:
    """Load and validate a YAML action script."""
    if not path.is_file():
        raise FileNotFoundError(f"action script not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"action script must be a YAML mapping: {path}")
    return ActionScript.model_validate(cast(dict[str, object], raw))


def run_action_script(script: ActionScript, *, seed_override: int | None = None) -> ScenarioRunResult:
    """Replay ``script`` from a fresh deterministic Phase A1 game."""
    seed = script.seed if seed_override is None else seed_override
    state = new_game(seed, player_stats=script.player_stats)
    rng = SeededRng(seed)
    turns: list[TurnResult] = []

    for action in script.actions:
        turn = run_turn(state, action, rng)
        turns.append(turn.model_copy(deep=True))
        state = turn.state

    final_hash = state_hash(state.model_dump(mode="json"))
    return ScenarioRunResult(script=script, state=state, turns=turns, final_hash=final_hash)


def assert_expected_hash(result: ScenarioRunResult) -> None:
    """Raise if a replay result does not match its checked-in expected hash."""
    expected = result.script.expected_hash
    if expected is None:
        raise ValueError(f"scenario {result.script.name!r} is missing expected_hash")
    if result.final_hash != expected:
        raise AssertionError(
            f"scenario {result.script.name!r} hash mismatch: "
            f"expected {expected}, got {result.final_hash}"
        )
