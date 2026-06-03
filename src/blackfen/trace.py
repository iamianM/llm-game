"""Trace packages and deterministic replay for Blackfen Road."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from src.blackfen.agents.intent import IntentParser
from src.blackfen.agents.narrator import Narrator
from src.blackfen.engine import run_turn
from src.blackfen.hash import state_hash
from src.blackfen.models import GameState, Intent, MechanicalResult, TurnRecord
from src.blackfen.new_game import new_game
from src.blackfen.rng import SeededRng
from src.blackfen.scenario import ActionScript, ScenarioRunResult, run_action_script

TRACE_SCHEMA_VERSION = 1
DEFAULT_TRACE_DIR = Path(".blackfen_traces")


class BlackfenTracePackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_schema_version: int = TRACE_SCHEMA_VERSION
    game_id: str = "blackfen_road"
    name: str
    seed: int
    player_name: str
    class_id: str
    actions: list[str] = Field(min_length=1)
    turns: list[TurnRecord]
    final_state: GameState
    final_hash: str
    fun_score: int = Field(ge=0, le=100)
    review_notes: list[str] = Field(default_factory=list)


class RecordedIntentParser:
    """Replay parser that consumes recorded intents instead of parsing text again."""

    def __init__(self, intents: list[Intent]) -> None:
        self._intents = intents
        self._index = 0

    def parse(self, _state: GameState, raw_text: str) -> Intent:
        if self._index >= len(self._intents):
            raise ValueError("recorded parser exhausted")
        intent = self._intents[self._index]
        self._index += 1
        if intent.raw_text != raw_text:
            raise ValueError(f"recorded intent text mismatch: expected {intent.raw_text!r}, got {raw_text!r}")
        return intent


class RecordedNarrator:
    """Replay narrator that consumes recorded narration."""

    def __init__(self, narrations: list[str]) -> None:
        self._narrations = narrations
        self._index = 0

    def narrate(self, _state: GameState, _result: MechanicalResult) -> str:
        if self._index >= len(self._narrations):
            raise ValueError("recorded narrator exhausted")
        narration = self._narrations[self._index]
        self._index += 1
        return narration


def build_trace_package(result: ScenarioRunResult, *, name: str | None = None) -> BlackfenTracePackage:
    """Create a replayable trace package from an action-script result."""
    fun_score, notes = score_fun(result.state)
    return BlackfenTracePackage(
        name=name or result.script.name,
        seed=result.state.seed,
        player_name=result.state.player.name,
        class_id=result.state.player.class_id,
        actions=list(result.script.actions),
        turns=result.turns,
        final_state=result.state,
        final_hash=result.final_hash,
        fun_score=fun_score,
        review_notes=notes,
    )


def build_trace_from_state(state: GameState, *, name: str) -> BlackfenTracePackage:
    """Package an interactive run that already carries turn records."""
    fun_score, notes = score_fun(state)
    return BlackfenTracePackage(
        name=name,
        seed=state.seed,
        player_name=state.player.name,
        class_id=state.player.class_id,
        actions=[turn.raw_text for turn in state.turns],
        turns=list(state.turns),
        final_state=state,
        final_hash=state_hash(state),
        fun_score=fun_score,
        review_notes=notes,
    )


def save_trace(package: BlackfenTracePackage, path: Path | None = None) -> Path:
    """Write a trace package and return its path."""
    target = path or DEFAULT_TRACE_DIR / f"{package.name}-{package.final_hash}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(package.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8")
    return target


def load_trace(path: Path) -> BlackfenTracePackage:
    return BlackfenTracePackage.model_validate_json(path.read_text(encoding="utf-8"))


def replay_trace(package: BlackfenTracePackage) -> ScenarioRunResult:
    """Replay a saved trace through the canonical engine using recorded agent outputs."""
    state = new_game(package.seed, player_name=package.player_name, class_id=package.class_id)
    rng = SeededRng(package.seed)
    parser: IntentParser = RecordedIntentParser([turn.intent for turn in package.turns])
    narrator: Narrator = RecordedNarrator([turn.narration for turn in package.turns])
    turns: list[TurnRecord] = []
    for expected in package.turns:
        if state_hash(state) != expected.input_hash:
            raise AssertionError(f"turn {expected.turn_index} input hash mismatch during replay")
        actual = run_turn(state, expected.raw_text, rng, parser=parser, narrator=narrator)
        turns.append(actual)
        if actual.output_hash != expected.output_hash:
            raise AssertionError(f"turn {expected.turn_index} output hash mismatch during replay")
    result = ScenarioRunResult(script=ActionScript(name=package.name, seed=package.seed, player_name=package.player_name, class_id=package.class_id, actions=list(package.actions), expected_hash=package.final_hash), state=state, turns=turns, final_hash=state_hash(state))
    if result.final_hash != package.final_hash:
        raise AssertionError(f"trace hash mismatch: expected {package.final_hash}, got {result.final_hash}")
    return result


def run_actions(actions: list[str], *, name: str, seed: int, player_name: str, class_id: str) -> ScenarioRunResult:
    script = ActionScript(name=name, seed=seed, player_name=player_name, class_id=class_id, actions=actions)
    return run_action_script(script)


def score_fun(state: GameState) -> tuple[int, list[str]]:
    """Score review usefulness of a run without judging prose quality."""
    score = 20
    notes: list[str] = []
    if len(state.visited_locations) >= 4:
        score += 15
        notes.append("The route used several locations.")
    if state.journal:
        score += 10
        notes.append("The player collected authored leads.")
    if state.resolved_encounters:
        score += min(20, len(state.resolved_encounters) * 10)
        notes.append("At least one encounter resolved.")
    if state.player.hp < state.player.max_hp:
        score += 10
        notes.append("The run created visible danger.")
    if state.status.value != "active":
        score += 20
        notes.append(f"The run reached a terminal state: {state.status.value}.")
    if state.companion.hp <= 0:
        score += 5
        notes.append("The companion was knocked out, creating stakes.")
    if not notes:
        notes.append("The run stayed shallow; add stronger exploration, danger, or story beats.")
    return min(100, score), notes
