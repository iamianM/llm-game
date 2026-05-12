"""Interaction outcome calculation and relationship deltas.

Design sources:
- 02-Core-Mechanics.md: Interaction Success Formula, Relationship Stats
- 05-Interaction-System.md: Success Calculation Details, Relationship Application

Implementation rule:
All math lives here or in nearby deterministic engine modules. The Narrator
receives the resolved result; it never calculates outcomes.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.game.engine.actions import ActionKind, PlayerAction, validate_action
from src.game.state.models import GameState, IslanderState, clamp_relationship
from src.game.state.rng import SeededRng


class MechanicalResult(BaseModel):
    """Resolved mechanical outcome from one player action."""

    model_config = ConfigDict(extra="forbid")

    action: PlayerAction
    success: bool
    roll: int | None = None
    success_chance: int | None = None
    relationship_deltas: dict[str, dict[str, int]] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


def apply_action(state: GameState, action: PlayerAction, rng: SeededRng) -> MechanicalResult:
    """Apply one valid action and mutate ``state``."""
    validate_action(state, action)
    if action.kind is ActionKind.TALK:
        return _apply_talk(state, action, rng)
    if action.kind is ActionKind.ADVANCE_PHASE:
        return MechanicalResult(action=action, success=True, tags=["phase"])
    raise ValueError(f"action is not implemented in Phase A1: {action.kind}")


def _apply_talk(state: GameState, action: PlayerAction, rng: SeededRng) -> MechanicalResult:
    target = _find_islander(state, action.target_id)
    chance = talk_success_chance(state, target)
    roll = rng.randint(1, 100)
    success = roll <= chance
    delta = 2 if success else 0
    target.relationship.affection = clamp_relationship(target.relationship.affection + delta)
    return MechanicalResult(
        action=action,
        success=success,
        roll=roll,
        success_chance=chance,
        relationship_deltas={target.id: {"affection": delta}},
        tags=["talk", "friendly"],
    )


def talk_success_chance(state: GameState, target: IslanderState) -> int:
    """Calculate Phase A1 TALK success chance.

    Uses the design rule that Banter contributes a 5% per-point success bonus
    and relationship value contributes a smaller familiarity bonus.
    """
    chance = 50 + (state.player.stats.banter * 5) + (target.relationship.affection // 5)
    return max(5, min(95, chance))


def _find_islander(state: GameState, target_id: str | None) -> IslanderState:
    if target_id is None:
        raise ValueError("target_id is required for TALK")
    for islander in state.islanders:
        if islander.id == target_id:
            return islander
    raise ValueError(f"unknown islander: {target_id}")
