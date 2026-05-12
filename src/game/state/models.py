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

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = 2


class Phase(StrEnum):
    """A minimal day clock for Phase A1."""

    MORNING = "morning"
    CHALLENGE = "challenge"
    AFTERNOON = "afternoon"
    TEXT = "text"
    EVENING = "evening"
    COMPLETE = "complete"


class PlayerStats(BaseModel):
    """Phase A1 player stats.

    Full design has five fixed stats. A1 intentionally starts with Charm and
    Banter only so the loop becomes playable before the full stat surface.
    """

    model_config = ConfigDict(extra="forbid")

    charm: int = Field(ge=3, le=9)
    banter: int = Field(ge=3, le=9)


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


class IslanderState(BaseModel):
    """Minimal NPC Islander state."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    archetype: str
    location_id: str
    relationship: RelationshipState = Field(default_factory=RelationshipState)


class GameState(BaseModel):
    """Canonical Phase A1 game state."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    seed: int
    turn_index: int = 0
    day: int = 1
    phase: Phase = Phase.MORNING
    location_id: str = "pool"
    player: PlayerState
    islanders: list[IslanderState]

    @property
    def is_terminal(self) -> bool:
        """Return whether the one-day A1 loop is complete."""
        return self.phase is Phase.COMPLETE


def clamp_relationship(value: int) -> int:
    """Clamp relationship values to the valid 0-100 range."""
    return max(0, min(100, value))


def new_game(seed: int) -> GameState:
    """Create the deterministic Phase A1 starting state."""
    return GameState(
        seed=seed,
        player=PlayerState(stats=PlayerStats(charm=6, banter=6)),
        islanders=[
            IslanderState(
                id="chloe",
                name="Chloe",
                archetype="sweetheart",
                location_id="pool",
                relationship=RelationshipState(affection=10),
            ),
            IslanderState(
                id="maya",
                name="Maya",
                archetype="joker",
                location_id="pool",
                relationship=RelationshipState(affection=8),
            ),
            IslanderState(
                id="liam",
                name="Liam",
                archetype="friend",
                location_id="pool",
                relationship=RelationshipState(affection=6),
            ),
        ],
    )
