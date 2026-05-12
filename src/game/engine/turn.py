"""One full game turn pipeline.

Design sources:
- 03-LLM-Architecture.md: The Handoff Point
- 05-Interaction-System.md: The Interaction Flow

Target flow:
validate action -> apply deterministic rules -> produce MechanicalResult ->
optionally narrate -> persist state and trace -> return next visible actions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.game.agents.narrator import mock_narration
from src.game.engine.actions import ActionKind, ActionSpec, PlayerAction, available_actions
from src.game.engine.phases import advance_phase
from src.game.engine.rules import MechanicalResult, apply_action
from src.game.engine.simulation import OffScreenEvent, simulate_off_screen
from src.game.state.models import GameState
from src.game.state.rng import SeededRng
from src.game.state.snapshot import state_hash


class TurnResult(BaseModel):
    """One completed turn returned to CLI, browser, or tests."""

    model_config = ConfigDict(extra="forbid")

    state: GameState
    mechanical_result: MechanicalResult
    narration: str
    available_actions: list[ActionSpec]
    state_hash: str
    off_screen_events: list[OffScreenEvent] = []


def run_turn(state: GameState, action: PlayerAction, rng: SeededRng) -> TurnResult:
    """Run one deterministic game turn."""
    result = apply_action(state, action, rng)
    off_screen_events: list[OffScreenEvent] = []
    if action.kind is ActionKind.ADVANCE_PHASE:
        advance_phase(state)
        off_screen_events = simulate_off_screen(
            state,
            rng.fork(f"day-{state.day}-phase-{state.phase.value}"),
        )
    state.turn_index += 1
    return TurnResult(
        state=state,
        mechanical_result=result,
        narration=mock_narration(state, result),
        available_actions=available_actions(state),
        state_hash=state_hash(state.model_dump(mode="json")),
        off_screen_events=off_screen_events,
    )
