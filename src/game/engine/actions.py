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

from src.game.state.models import GameState


class ActionKind(StrEnum):
    """Canonical action vocabulary shared by engine, CLI, browser, and tests."""

    TALK = "talk"
    FLIRT = "flirt"
    LISTEN = "listen"
    LEAVE = "leave"
    ADVANCE_PHASE = "advance_phase"


class PlayerAction(BaseModel):
    """One player action submitted by CLI, browser, or scenario fixtures."""

    model_config = ConfigDict(extra="forbid")

    kind: ActionKind
    target_id: str | None = None


class ActionSpec(BaseModel):
    """A valid action surfaced to the player."""

    model_config = ConfigDict(extra="forbid")

    action: PlayerAction
    label: str


def available_actions(state: GameState) -> list[ActionSpec]:
    """Return valid actions for the current state."""
    if state.is_terminal:
        return []

    actions = [
        spec
        for islander in state.islanders
        if islander.location_id == state.location_id
        for spec in (
            ActionSpec(
                action=PlayerAction(kind=ActionKind.TALK, target_id=islander.id),
                label=f"Talk to {islander.name}",
            ),
            ActionSpec(
                action=PlayerAction(kind=ActionKind.FLIRT, target_id=islander.id),
                label=f"Flirt with {islander.name}",
            ),
        )
    ]
    actions.append(
        ActionSpec(
            action=PlayerAction(kind=ActionKind.ADVANCE_PHASE),
            label="Advance phase",
        )
    )
    return actions


def validate_action(state: GameState, action: PlayerAction) -> None:
    """Raise if ``action`` is not valid for ``state``."""
    valid = [spec.action for spec in available_actions(state)]
    if action not in valid:
        raise ValueError(f"invalid action for current state: {action.model_dump()}")
