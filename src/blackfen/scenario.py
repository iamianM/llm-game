"""Deterministic action-script replay for Blackfen Road."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.blackfen.agents.intent import LocalIntentParser
from src.blackfen.agents.narrator import MockNarrator
from src.blackfen.engine import run_turn
from src.blackfen.hash import state_hash
from src.blackfen.models import GameState, TurnRecord
from src.blackfen.new_game import new_game
from src.blackfen.rng import SeededRng


class ActionScript(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    seed: int
    player_name: str = "You"
    class_id: str = "fighter"
    actions: list[str] = Field(min_length=1)
    expected_hash: str | None = None


class ScenarioRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script: ActionScript
    state: GameState
    turns: list[TurnRecord]
    final_hash: str


def load_action_script(path: Path) -> ActionScript:
    if not path.is_file():
        raise FileNotFoundError(f"action script not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"action script must be a YAML mapping: {path}")
    return ActionScript.model_validate(cast(dict[str, object], raw))


def run_action_script(script: ActionScript, *, seed_override: int | None = None) -> ScenarioRunResult:
    seed = script.seed if seed_override is None else seed_override
    state = new_game(seed, player_name=script.player_name, class_id=script.class_id)
    rng = SeededRng(seed)
    turns: list[TurnRecord] = []
    parser = LocalIntentParser()
    narrator = MockNarrator()
    for action in script.actions:
        turns.append(run_turn(state, action, rng, parser=parser, narrator=narrator))
    return ScenarioRunResult(script=script, state=state, turns=turns, final_hash=state_hash(state))


def assert_expected_hash(result: ScenarioRunResult) -> None:
    expected = result.script.expected_hash
    if expected is None:
        raise ValueError(f"scenario {result.script.name!r} is missing expected_hash")
    if result.final_hash != expected:
        raise AssertionError(f"scenario {result.script.name!r} hash mismatch: expected {expected}, got {result.final_hash}")
