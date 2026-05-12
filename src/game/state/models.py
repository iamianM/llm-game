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
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = 5


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


class Mood(StrEnum):
    """Current Islander mood for conversation prompts and intent modifiers."""

    HAPPY = "happy"
    FLIRTY = "flirty"
    UPSET = "upset"
    ANXIOUS = "anxious"
    ANGRY = "angry"
    CONTENT = "content"


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
    public_perception: int = Field(default=50, ge=0, le=100)
    eliminated: bool = False


class RelationshipState(BaseModel):
    """Player-facing relationship state for one islander."""

    model_config = ConfigDict(extra="forbid")

    affection: int = Field(default=0, ge=0, le=100)
    chemistry: int = Field(default=0, ge=0, le=100)
    trust: int = Field(default=0, ge=0, le=100)
    friendship: int = Field(default=0, ge=0, le=100)


class RelationshipDelta(BaseModel):
    """Typed relationship changes for one target."""

    model_config = ConfigDict(extra="forbid")

    affection: int = 0
    chemistry: int = 0
    trust: int = 0
    friendship: int = 0


class IslanderState(BaseModel):
    """Minimal NPC Islander state."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    archetype: str
    location_id: Location
    relationship: RelationshipState = Field(default_factory=RelationshipState)
    public_perception: int = Field(default=50, ge=0, le=100)
    eliminated: bool = False
    mood: Mood = Mood.CONTENT


class Couple(BaseModel):
    """Two islanders paired by the deterministic ceremony rules."""

    model_config = ConfigDict(extra="forbid")

    partner_a_id: str
    partner_b_id: str
    formed_on_day: int


class FollowUpOption(BaseModel):
    """One contextual follow-up choice in an open conversation."""

    model_config = ConfigDict(extra="forbid")

    text: str
    intent_kind: str
    stat_used: Literal["charm", "banter", "eq", "graft", "loyalty"] | None
    risk: Literal["safe", "low", "medium", "high"]
    tone: str


class FollowUpMenu(BaseModel):
    """Contextual menu generated after an NPC reply."""

    model_config = ConfigDict(extra="forbid")

    options: list[FollowUpOption] = Field(min_length=2, max_length=4)
    npc_will_leave: bool
    npc_exit_line: str | None = None


class ExchangeRecord(BaseModel):
    """One exchange retained inside an active conversation."""

    model_config = ConfigDict(extra="forbid")

    turn_index: int
    intent_id: str
    player_dialogue: str
    npc_dialogue: str
    npc_tone: str
    npc_mood_after: Mood
    success: bool
    tags: list[str] = Field(default_factory=list)
    relationship_deltas: dict[str, RelationshipDelta] = Field(default_factory=dict)


class Conversation(BaseModel):
    """A single active one-on-one conversation."""

    model_config = ConfigDict(extra="forbid")

    target_id: str
    started_on_turn: int
    started_on_day: int
    exchanges: list[ExchangeRecord] = Field(default_factory=list)
    accumulated_tags: list[str] = Field(default_factory=list)
    status: Literal["open", "closing", "closed"] = "open"
    departure_probability_last: int = 0
    pending_options: FollowUpMenu | None = None


class GameState(BaseModel):
    """Canonical deterministic game state."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    seed: int
    turn_index: int = 0
    day: int = 1
    phase: Phase = Phase.MORNING
    location_id: Location = Location.POOL
    player: PlayerState
    islanders: list[IslanderState]
    couples: list[Couple] = Field(default_factory=list)
    active_conversation: Conversation | None = None

    @property
    def is_terminal(self) -> bool:
        """Return whether the current run is terminal."""
        return self.phase is Phase.COMPLETE


def clamp_relationship(value: int) -> int:
    """Clamp relationship values to the valid 0-100 range."""
    return max(0, min(100, value))


def new_game(seed: int, *, player_stats: PlayerStats | None = None) -> GameState:
    """Create the deterministic starting state."""
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
