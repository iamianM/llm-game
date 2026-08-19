"""Pydantic models for runtime content frontmatter."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ArchetypeContent(BaseModel):
    """Narrator-facing archetype flavor."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    body: str


class LocationContent(BaseModel):
    """Narrator-facing location flavor."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    body: str


class PlayerArchetypeContent(BaseModel):
    """Player-facing archetype content."""

    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str
    stat_bonus_name: str
    stat_bonus_value: int
    starter_advantage: str
    body: str


class ChallengeContent(BaseModel):
    """Narrator-facing daily challenge flavor."""

    model_config = ConfigDict(extra="forbid")

    id: str
    day: int
    kind: str
    body: str


class ProducerTextContent(BaseModel):
    """Scheduled producer text content."""

    model_config = ConfigDict(extra="forbid")

    id: str
    day: int
    kind: str
    body: str


class FlushOfHeartsCastContent(BaseModel):
    """Authored Flush of Hearts cast member content."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    gender: str
    archetype: str
    body: str


class ContentIndex(BaseModel):
    """Loaded runtime content indexed by id."""

    model_config = ConfigDict(extra="forbid")

    archetypes: dict[str, ArchetypeContent]
    locations: dict[str, LocationContent]
    player_archetypes: dict[str, PlayerArchetypeContent]
    challenges: dict[str, ChallengeContent]
    producer_texts: dict[str, ProducerTextContent]
    flush_of_hearts_cast: dict[str, FlushOfHeartsCastContent]
    backstories: dict[str, str]
