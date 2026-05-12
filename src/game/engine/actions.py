"""Available action generation and action validation.

Design sources:
- 05-Interaction-System.md: Hybrid Menu System, Interaction Flow
- 06-Location-System.md: Location-specific actions

Implementation rule:
Action mechanics live in Python. Optional markdown content may provide
narrator-facing flavor, but it must not decide whether an action is valid.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from src.game.engine.intents import available_intents_for, get_intent
from src.game.state.models import GameState, Location, Phase


class ActionKind(StrEnum):
    """Canonical action vocabulary shared by engine, CLI, browser, and tests."""

    START_CONVERSATION = "start_conversation"
    RESPOND_WITH = "respond_with"
    END_CONVERSATION = "end_conversation"
    MOVE = "move"
    RECOUPLE = "recouple"
    ADVANCE_PHASE = "advance_phase"


class PlayerAction(BaseModel):
    """One player action submitted by CLI, browser, or scenario fixtures."""

    model_config = ConfigDict(extra="forbid")

    kind: ActionKind
    target_id: str | None = None
    intent_id: str | None = None
    option_index: int | None = None


class ActionSpec(BaseModel):
    """A valid action surfaced to the player."""

    model_config = ConfigDict(extra="forbid")

    action: PlayerAction
    label: str


def available_actions(state: GameState) -> list[ActionSpec]:
    """Return valid actions for the current state."""
    if state.is_terminal:
        return []

    actions: list[ActionSpec] = []
    for islander in state.islanders:
        if islander.location_id != state.location_id or islander.eliminated:
            continue
        actions.append(
            ActionSpec(
                action=PlayerAction(kind=ActionKind.START_CONVERSATION, target_id=islander.id),
                label=f"Talk to {islander.name}",
            )
        )
    actions.append(
        ActionSpec(action=PlayerAction(kind=ActionKind.END_CONVERSATION), label="Leave the chat")
    )
    if state.phase in {Phase.MORNING, Phase.AFTERNOON}:
        for location in Location:
            if location != state.location_id:
                actions.append(
                    ActionSpec(
                        action=PlayerAction(kind=ActionKind.MOVE, target_id=location.value),
                        label=f"Move to {location.value}",
                    )
                )
    actions.append(
        ActionSpec(
            action=PlayerAction(kind=ActionKind.ADVANCE_PHASE),
            label="Advance phase",
        )
    )
    return actions


def validate_action(state: GameState, action: PlayerAction) -> None:
    """Raise if ``action`` is not valid for ``state``."""
    if action.kind is ActionKind.START_CONVERSATION:
        if action.target_id is None or action.intent_id is None:
            raise ValueError("START_CONVERSATION requires target_id and intent_id")
        valid_intents = {intent.id for intent in available_intents_for(state, action.target_id)}
        if action.intent_id not in valid_intents:
            get_intent(action.intent_id)
            raise ValueError(f"intent is locked or unavailable: {action.model_dump()}")
        return
    valid = [spec.action for spec in available_actions(state)]
    if action not in valid:
        raise ValueError(f"invalid action for current state: {action.model_dump()}")
