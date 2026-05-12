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

from src.game.agents.event_narrator import (
    EventNarration,
    EventNarratorFn,
    mock_event_narration,
)
from src.game.agents.islander_voice import Exchange, IslanderVoiceFn, mock_islander_voice
from src.game.engine.actions import ActionKind, ActionSpec, PlayerAction, available_actions
from src.game.engine.ceremonies import CeremonyEvent, arrive_bombshell, recoupling
from src.game.engine.phases import advance_phase
from src.game.engine.rules import MechanicalResult, apply_action
from src.game.engine.simulation import OffScreenEvent, simulate_off_screen
from src.game.state.models import GameState
from src.game.state.rng import SeededRng
from src.game.state.snapshot import state_hash, state_hash_payload


class TurnResult(BaseModel):
    """One completed turn returned to CLI, browser, or tests."""

    model_config = ConfigDict(extra="forbid")

    state: GameState
    mechanical_result: MechanicalResult
    exchange: Exchange | None = None
    event_narration: EventNarration | None = None
    available_actions: list[ActionSpec]
    state_hash: str
    off_screen_events: list[OffScreenEvent] = []
    ceremony_events: list[CeremonyEvent] = []


def run_turn(
    state: GameState,
    action: PlayerAction,
    rng: SeededRng,
    islander_voice: IslanderVoiceFn | None = None,
    event_narrator: EventNarratorFn | None = None,
) -> TurnResult:
    """Run one deterministic game turn."""
    result = apply_action(state, action, rng)
    off_screen_events: list[OffScreenEvent] = []
    ceremony_events: list[CeremonyEvent] = []
    if action.kind is ActionKind.RECOUPLE:
        ceremony = recoupling(state, action.target_id)
        ceremony_events.extend(_recoupling_events(ceremony.eliminated_id))
    if action.kind is ActionKind.ADVANCE_PHASE:
        if state.phase.value == "evening" and state.day in {3, 5}:
            ceremony = recoupling(state)
            ceremony_events.extend(_recoupling_events(ceremony.eliminated_id))
        advance_phase(state)
        if state.day == 4 and state.phase.value == "morning":
            bombshell = arrive_bombshell(state)
            ceremony_events.append(
                CeremonyEvent(
                    kind="bombshell",
                    message=f"Bombshell arrived: {bombshell.name} enters the villa.",
                    islander_id=bombshell.id,
                )
            )
        off_screen_events = simulate_off_screen(
            state,
            rng.fork(f"day-{state.day}-phase-{state.phase.value}"),
        )
    state.turn_index += 1
    exchange = None
    if action.kind in {ActionKind.START_CONVERSATION, ActionKind.RESPOND_WITH}:
        speak = mock_islander_voice if islander_voice is None else islander_voice
        exchange = speak(state, result)
    event_narration = None
    if ceremony_events:
        narrate_event = mock_event_narration if event_narrator is None else event_narrator
        event_narration = narrate_event(state, ceremony_events)
    return TurnResult(
        state=state,
        mechanical_result=result,
        exchange=exchange,
        event_narration=event_narration,
        available_actions=available_actions(state),
        state_hash=state_hash(state_hash_payload(state)),
        off_screen_events=off_screen_events,
        ceremony_events=ceremony_events,
    )


def _recoupling_events(eliminated_id: str | None) -> list[CeremonyEvent]:
    events = [CeremonyEvent(kind="recoupling", message="Recoupling ceremony completed.")]
    if eliminated_id is not None:
        events.append(
            CeremonyEvent(
                kind="elimination",
                message=f"Dumping decision: {eliminated_id} leaves the villa.",
                islander_id=eliminated_id,
            )
        )
    return events
