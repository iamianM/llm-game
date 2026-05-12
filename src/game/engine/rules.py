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
from src.game.state.models import GameState, IslanderState, Location, clamp_relationship
from src.game.state.rng import SeededRng

TALK_SUCCESS_AFFECTION_DELTA = 2
FLIRT_SUCCESS_AFFECTION_DELTA = 2
FLIRT_SUCCESS_CHEMISTRY_DELTA = 5
FLIRT_MISS_CHEMISTRY_DELTA = -1
BOLD_FLIRT_SUCCESS_AFFECTION_DELTA = 3
BOLD_FLIRT_SUCCESS_CHEMISTRY_DELTA = 8
BOLD_FLIRT_MISS_CHEMISTRY_DELTA = -3
LISTEN_SUCCESS_TRUST_DELTA = 3
LISTEN_FRIENDSHIP_DELTA = 1


class RelationshipDelta(BaseModel):
    """Typed relationship changes for one target."""

    model_config = ConfigDict(extra="forbid")

    affection: int = 0
    chemistry: int = 0
    trust: int = 0
    friendship: int = 0


class MechanicalResult(BaseModel):
    """Resolved mechanical outcome from one player action."""

    model_config = ConfigDict(extra="forbid")

    action: PlayerAction
    success: bool
    roll: int | None = None
    success_chance: int | None = None
    relationship_deltas: dict[str, RelationshipDelta] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


def apply_action(state: GameState, action: PlayerAction, rng: SeededRng) -> MechanicalResult:
    """Apply one valid action and mutate ``state``."""
    validate_action(state, action)
    if action.kind is ActionKind.TALK:
        result = _apply_talk(state, action, rng)
        update_public_perception(state, action, result)
        return result
    if action.kind is ActionKind.FLIRT:
        result = _apply_flirt(state, action, rng)
        update_public_perception(state, action, result)
        return result
    if action.kind is ActionKind.BOLD_FLIRT:
        result = _apply_bold_flirt(state, action, rng)
        update_public_perception(state, action, result)
        return result
    if action.kind is ActionKind.LISTEN:
        result = _apply_listen(state, action, rng)
        update_public_perception(state, action, result)
        return result
    if action.kind is ActionKind.LEAVE:
        return MechanicalResult(action=action, success=True, tags=["disengaged"])
    if action.kind is ActionKind.MOVE:
        return _apply_move(state, action)
    if action.kind is ActionKind.ADVANCE_PHASE:
        return MechanicalResult(action=action, success=True, tags=["phase"])
    raise ValueError(f"action is not implemented in Phase A1: {action.kind}")


def _apply_talk(state: GameState, action: PlayerAction, rng: SeededRng) -> MechanicalResult:
    target = _find_islander(state, action.target_id)
    chance = talk_success_chance(state, target)
    roll = rng.randint(1, 100)
    success = roll <= chance
    delta = TALK_SUCCESS_AFFECTION_DELTA if success else 0
    target.relationship.affection = clamp_relationship(target.relationship.affection + delta)
    return MechanicalResult(
        action=action,
        success=success,
        roll=roll,
        success_chance=chance,
        relationship_deltas={target.id: RelationshipDelta(affection=delta)},
        tags=["talk", "friendly"],
    )


def _apply_flirt(state: GameState, action: PlayerAction, rng: SeededRng) -> MechanicalResult:
    target = _find_islander(state, action.target_id)
    chance = flirt_success_chance(state, target)
    roll = rng.randint(1, 100)
    success = roll <= chance
    affection_delta = FLIRT_SUCCESS_AFFECTION_DELTA if success else 0
    chemistry_delta = FLIRT_SUCCESS_CHEMISTRY_DELTA if success else FLIRT_MISS_CHEMISTRY_DELTA
    target.relationship.affection = clamp_relationship(
        target.relationship.affection + affection_delta
    )
    target.relationship.chemistry = clamp_relationship(
        target.relationship.chemistry + chemistry_delta
    )
    return MechanicalResult(
        action=action,
        success=success,
        roll=roll,
        success_chance=chance,
        relationship_deltas={
            target.id: RelationshipDelta(
                affection=affection_delta,
                chemistry=chemistry_delta,
            )
        },
        tags=["flirty"] if success else ["awkward"],
    )


def _apply_bold_flirt(state: GameState, action: PlayerAction, rng: SeededRng) -> MechanicalResult:
    target = _find_islander(state, action.target_id)
    chance = bold_flirt_success_chance(state, target)
    roll = rng.randint(1, 100)
    success = roll <= chance
    affection_delta = BOLD_FLIRT_SUCCESS_AFFECTION_DELTA if success else 0
    chemistry_delta = (
        BOLD_FLIRT_SUCCESS_CHEMISTRY_DELTA if success else BOLD_FLIRT_MISS_CHEMISTRY_DELTA
    )
    target.relationship.affection = clamp_relationship(
        target.relationship.affection + affection_delta
    )
    target.relationship.chemistry = clamp_relationship(
        target.relationship.chemistry + chemistry_delta
    )
    return MechanicalResult(
        action=action,
        success=success,
        roll=roll,
        success_chance=chance,
        relationship_deltas={
            target.id: RelationshipDelta(affection=affection_delta, chemistry=chemistry_delta)
        },
        tags=["bold", "flirty"] if success else ["bold", "awkward"],
    )


def _apply_listen(state: GameState, action: PlayerAction, rng: SeededRng) -> MechanicalResult:
    target = _find_islander(state, action.target_id)
    chance = listen_success_chance(state, target)
    roll = rng.randint(1, 100)
    success = roll <= chance
    trust_delta = LISTEN_SUCCESS_TRUST_DELTA if success else 0
    target.relationship.trust = clamp_relationship(target.relationship.trust + trust_delta)
    target.relationship.friendship = clamp_relationship(
        target.relationship.friendship + LISTEN_FRIENDSHIP_DELTA
    )
    return MechanicalResult(
        action=action,
        success=success,
        roll=roll,
        success_chance=chance,
        relationship_deltas={
            target.id: RelationshipDelta(
                trust=trust_delta,
                friendship=LISTEN_FRIENDSHIP_DELTA,
            )
        },
        tags=["listen", "supportive"],
    )


def talk_success_chance(state: GameState, target: IslanderState) -> int:
    """Calculate Phase A1 TALK success chance.

    Uses the design rule that Banter contributes a 5% per-point success bonus
    and relationship value contributes a smaller familiarity bonus.
    """
    chance = 50 + (state.player.stats.banter * 5) + (target.relationship.affection // 5)
    return max(5, min(95, chance))


def flirt_success_chance(state: GameState, target: IslanderState) -> int:
    """Calculate Phase A2 FLIRT success chance."""
    chance = 40 + (state.player.stats.charm * 5) + (target.relationship.chemistry // 4)
    return max(5, min(95, chance))


def bold_flirt_success_chance(state: GameState, target: IslanderState) -> int:
    """Calculate high-risk Phase A3 BOLD_FLIRT success chance."""
    chance = 30 + (state.player.stats.graft * 6) + (target.relationship.chemistry // 5)
    return max(5, min(95, chance))


def listen_success_chance(state: GameState, target: IslanderState) -> int:
    """Calculate Phase A3 LISTEN success chance."""
    chance = 45 + (state.player.stats.eq * 5) + (target.relationship.affection // 5)
    return max(5, min(95, chance))


def _apply_move(state: GameState, action: PlayerAction) -> MechanicalResult:
    if action.target_id is None:
        raise ValueError("target_id is required for MOVE")
    state.location_id = Location(action.target_id)
    return MechanicalResult(action=action, success=True, tags=["move"])


def _find_islander(state: GameState, target_id: str | None) -> IslanderState:
    if target_id is None:
        raise ValueError("target_id is required for TALK")
    for islander in state.islanders:
        if islander.id == target_id:
            return islander
    raise ValueError(f"unknown islander: {target_id}")


def update_public_perception(
    state: GameState,
    action: PlayerAction,
    result: MechanicalResult,
) -> None:
    """Apply small deterministic public-perception movement."""
    delta = 0
    if action.kind is ActionKind.LISTEN and result.success:
        delta = 2
    elif action.kind is ActionKind.BOLD_FLIRT and not result.success:
        delta = -2
    elif action.kind is ActionKind.FLIRT and not result.success:
        delta = -1
    state.player.public_perception = clamp_relationship(state.player.public_perception + delta)
