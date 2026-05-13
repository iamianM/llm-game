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

from src.game.agents.contextual_options import ContextualOptionsFn, mock_follow_up_menu
from src.game.agents.islander_voice import Exchange
from src.game.agents.player_autopilot import PolicyDecision
from src.game.agents.villa_orchestrator import VillaOrchestratorFn, VillaUpdate
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.character_creation import create_character
from src.game.engine.phases import PHASE_BUDGETS
from src.game.engine.rules import MechanicalResult
from src.game.engine.turn import TurnResult, run_turn
from src.game.state.models import (
    CharacterCreation,
    Couple,
    FollowUpMenu,
    GameState,
    Location,
    Phase,
    PlayerStats,
    RelationshipState,
    new_game,
)
from src.game.state.phase_clock import PhaseClock
from src.game.state.rng import SeededRng
from src.game.state.snapshot import state_hash, state_hash_payload


class ActionScript(BaseModel):
    """A YAML action script for deterministic replay."""

    model_config = ConfigDict(extra="forbid")

    name: str
    seed: int
    player_stats: PlayerStats | None = None
    character_creation: CharacterCreation | None = None
    initial_day: int | None = None
    initial_phase: Phase | None = None
    initial_location: Location | None = None
    initial_relationships: dict[str, RelationshipState] | None = None
    initial_couples: list[Couple] | None = None
    autopilot_decisions: list[PolicyDecision] | None = None
    villa_updates: list[VillaUpdate | None] | None = None
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
    """Replay ``script`` from a fresh deterministic game."""
    seed = script.seed if seed_override is None else seed_override
    state = new_game(seed, player_stats=script.player_stats)
    _apply_initial_state(state, script)
    if script.character_creation is not None:
        create_character(
            state,
            archetype_id=script.character_creation.archetype_id,
            gender=script.character_creation.gender,
            stats=script.character_creation.stats,
            rerolled=script.character_creation.rerolled,
        )
    rng = SeededRng(seed)
    turns: list[TurnResult] = []
    contextual_options = _scripted_contextual_options(script.actions, script.villa_updates)
    villa_orchestrator = _scripted_villa_updates(script.villa_updates)

    for action in script.actions:
        turn = run_turn(
            state,
            action,
            rng,
            contextual_options=contextual_options,
            villa_orchestrator=villa_orchestrator,
        )
        turns.append(turn.model_copy(deep=True))
        state = turn.state

    final_hash = state_hash(state_hash_payload(state))
    return ScenarioRunResult(script=script, state=state, turns=turns, final_hash=final_hash)


def _apply_initial_state(state: GameState, script: ActionScript) -> None:
    if script.initial_day is not None:
        state.day = script.initial_day
    if script.initial_phase is not None:
        state.phase = script.initial_phase
        state.phase_clock = PhaseClock(
            phase=state.phase.value,
            budget_minutes=PHASE_BUDGETS[state.phase],
        )
    if script.initial_location is not None:
        state.location_id = script.initial_location
    if script.initial_couples is not None:
        state.couples = [couple.model_copy(deep=True) for couple in script.initial_couples]
    if script.initial_relationships is not None:
        for islander in state.islanders:
            relationship = script.initial_relationships.get(islander.id)
            if relationship is not None:
                islander.relationship = relationship.model_copy(deep=True)


def _scripted_contextual_options(
    actions: list[PlayerAction],
    villa_updates: list[VillaUpdate | None] | None,
) -> ContextualOptionsFn:
    planned = _planned_follow_up_intents(actions, villa_updates)
    index = 0

    def contextual_options(
        _state: GameState,
        _result: MechanicalResult,
        _exchange: Exchange,
        _probability: int,
    ) -> FollowUpMenu:
        nonlocal index
        intent_kind = planned[index] if index < len(planned) else None
        index += 1
        if intent_kind is None:
            return mock_follow_up_menu(npc_will_leave=True)
        return mock_follow_up_menu(intent_kind=intent_kind)

    return contextual_options


def _scripted_villa_updates(updates: list[VillaUpdate | None] | None) -> VillaOrchestratorFn | None:
    if updates is None:
        return None
    index = 0

    def villa_orchestrator(_state: GameState) -> VillaUpdate:
        nonlocal index
        update = updates[index] if index < len(updates) else None
        index += 1
        return VillaUpdate() if update is None else update

    return villa_orchestrator


def _planned_follow_up_intents(
    actions: list[PlayerAction],
    villa_updates: list[VillaUpdate | None] | None,
) -> list[str | None]:
    planned: list[str | None] = []
    for index, action in enumerate(actions):
        if action.kind not in {ActionKind.START_CONVERSATION, ActionKind.RESPOND_WITH}:
            continue
        update = None if villa_updates is None or index >= len(villa_updates) else villa_updates[index]
        if update is not None and update.npc_summoned_elsewhere:
            planned.append("joke_back")
            continue
        next_action = actions[index + 1] if index + 1 < len(actions) else None
        if next_action is not None and next_action.kind is ActionKind.RESPOND_WITH:
            planned.append(next_action.intent_id or "joke_back")
        elif next_action is not None and next_action.kind is ActionKind.END_CONVERSATION:
            planned.append("end_softly")
        else:
            planned.append(None)
    return planned


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
