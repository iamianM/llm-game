"""Shared mechanical result models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.game.engine.actions import PlayerAction
from src.game.engine.private_chat import PrivateChatAttempt
from src.game.state.models import Location, RelationshipDelta

# Closed set of non-fatal engine anomalies worth surfacing in the review packet.
# These are degradations the engine handled gracefully (no dead-screen) but that
# should still be *countable* rather than silently swallowed (ENGINEERING R16).
MechanicalAnomaly = Literal["gossip_stale_noop"]


class ChanceBreakdown(BaseModel):
    """Auditable inputs that produced a final success chance."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    base: int
    stat_name: str | None = None
    stat_value: int | None = None
    stat_multiplier: int = 0
    stat_contribution: int = 0
    affection_value: int = 0
    affection_divisor: int = 1
    affection_contribution: int = 0
    risk: str | None = None
    risk_modifier: int = 0
    mood_modifier: int = 0
    compatibility_bonus: int = 0
    dealbreaker_penalty: int = 0
    attachment_delta: RelationshipDelta = Field(default_factory=RelationshipDelta)
    pre_cap: int
    cap: int
    floor: int
    final_chance: int


class ForcedMovement(BaseModel):
    """Engine-owned movement caused by the player's direct action."""

    model_config = ConfigDict(extra="forbid")

    actor_id: str
    kind: str
    target_location: Location


class MechanicalResult(BaseModel):
    """Resolved mechanical outcome from one player action."""

    model_config = ConfigDict(extra="forbid")

    action: PlayerAction
    success: bool
    roll: int | None = None
    success_chance: int | None = None
    chance_breakdown: ChanceBreakdown | None = None
    relationship_deltas: dict[str, RelationshipDelta] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    private_chat_attempt: PrivateChatAttempt | None = None
    forced_movements: list[ForcedMovement] = Field(default_factory=list)
    audience_delta: int = 0
    audience_reason: str | None = None
    proposal_outcome: dict[str, object] | None = None
    anomalies: list[MechanicalAnomaly] = Field(default_factory=list)
