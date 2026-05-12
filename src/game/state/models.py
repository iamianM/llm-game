"""Pydantic models for canonical game state.

Design sources:
- 04-State-Management.md: Islander State, Player State, Villa State
- 02-Core-Mechanics.md: Player stats and relationship stats

Implementation rule:
The browser may render a filtered view of these models, but it does not own
canonical game state.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = 3


class Phase(StrEnum):
    """The day clock for the playable v0 loop."""

    MORNING = "morning"
    CHALLENGE = "challenge"
    AFTERNOON = "afternoon"
    TEXT = "text"
    EVENING = "evening"
    COMPLETE = "complete"


class Location(StrEnum):
    """Discrete villa locations."""

    POOL = "pool"
    KITCHEN = "kitchen"
    TERRACE = "terrace"
    BEDROOM = "bedroom"


class PlayerStats(BaseModel):
    """Five fixed player stats with the A3 30-point budget."""

    model_config = ConfigDict(extra="forbid")

    charm: int = Field(ge=3, le=9)
    banter: int = Field(ge=3, le=9)
    eq: int = Field(ge=3, le=9)
    graft: int = Field(ge=3, le=9)
    loyalty: int = Field(ge=3, le=9)

    @model_validator(mode="after")
    def validate_budget(self) -> PlayerStats:
        """Reject stat allocations above the starting 30-point budget."""
        total = self.charm + self.banter + self.eq + self.graft + self.loyalty
        if total > 30:
            raise ValueError("player stat total cannot exceed 30")
        return self


class PlayerState(BaseModel):
    """Player identity and stats."""

    model_config = ConfigDict(extra="forbid")

    id: str = "player"
    name: str = "You"
    stats: PlayerStats


class RelationshipState(BaseModel):
    """Minimal relationship state for Phase A1."""

    model_config = ConfigDict(extra="forbid")

    affection: int = Field(default=0, ge=0, le=100)
    chemistry: int = Field(default=0, ge=0, le=100)
    trust: int = Field(default=0, ge=0, le=100)
    friendship: int = Field(default=0, ge=0, le=100)


class IslanderState(BaseModel):
    """Minimal NPC Islander state."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    archetype: str
    location_id: Location
    relationship: RelationshipState = Field(default_factory=RelationshipState)


class GameState(BaseModel):
    """Canonical Phase A1 game state."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    seed: int
    turn_index: int = 0
    day: int = 1
    phase: Phase = Phase.MORNING
    location_id: Location = Location.POOL
    player: PlayerState
    islanders: list[IslanderState]

    @property
    def is_terminal(self) -> bool:
        """Return whether the current run is terminal."""
        return self.phase is Phase.COMPLETE


def clamp_relationship(value: int) -> int:
    """Clamp relationship values to the valid 0-100 range."""
    return max(0, min(100, value))


def new_game(seed: int, *, player_stats: PlayerStats | None = None) -> GameState:
    """Create the deterministic Phase A1 starting state."""
    return GameState(
        seed=seed,
        player=PlayerState(
            stats=player_stats
            if player_stats is not None
            else PlayerStats(charm=6, banter=6, eq=6, graft=6, loyalty=6)
        ),
        islanders=[
            IslanderState(
                id="chloe",
                name="Chloe",
                archetype="sweetheart",
                location_id=Location.POOL,
                relationship=RelationshipState(affection=10),
            ),
            IslanderState(
                id="maya",
                name="Maya",
                archetype="joker",
                location_id=Location.KITCHEN,
                relationship=RelationshipState(affection=8),
            ),
            IslanderState(
                id="liam",
                name="Liam",
                archetype="friend",
                location_id=Location.TERRACE,
                relationship=RelationshipState(affection=6),
            ),
        ],
    )
