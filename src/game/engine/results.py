"""Shared mechanical result models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.game.engine.actions import PlayerAction
from src.game.engine.pull import PullAttempt
from src.game.state.models import RelationshipDelta


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
    pre_cap: int
    cap: int
    floor: int
    final_chance: int


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
    pull_attempt: PullAttempt | None = None
