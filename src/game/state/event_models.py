"""State models for scheduled events."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RelationshipDelta(BaseModel):
    """Typed relationship changes for one target."""

    model_config = ConfigDict(extra="forbid")

    affection: int = 0
    chemistry: int = 0
    trust: int = 0
    friendship: int = 0


class AudienceEntry(BaseModel):
    """One ranked audience score row."""

    model_config = ConfigDict(extra="forbid")

    rank: int
    couple: list[str]
    score: int
    is_player_couple: bool = False


class AudienceSnapshot(BaseModel):
    """End-of-day audience ranking surfaced to traces and reports."""

    model_config = ConfigDict(extra="forbid")

    day: int
    entries: list[AudienceEntry] = Field(default_factory=list)


class Challenge(BaseModel):
    """One scheduled daily challenge and its mechanical result."""

    model_config = ConfigDict(extra="forbid")

    id: str
    day: int
    kind: str
    stat_tested: Literal["charm", "banter", "eq", "graft", "loyalty", "combined"]
    participants: list[str] = Field(default_factory=list)
    player_choice: str | None = None
    result: Literal["success", "failure"] | None = None
    deltas: dict[str, RelationshipDelta] = Field(default_factory=dict)


class ProducerText(BaseModel):
    """A scheduled producer text shown during the text phase."""

    model_config = ConfigDict(extra="forbid")

    id: str
    day: int
    phase: Literal["text"] = "text"
    kind: str
    body: str
    triggers: list[str] = Field(default_factory=list)


class GroupDate(BaseModel):
    """A scheduled two-NPC group date hook."""

    model_config = ConfigDict(extra="forbid")

    id: str
    participants: list[str]
    location: Literal["pool", "kitchen", "terrace", "bedroom"]
    day: int
    pending: bool = True
