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


class ContentIndex(BaseModel):
    """Loaded runtime content indexed by id."""

    model_config = ConfigDict(extra="forbid")

    archetypes: dict[str, ArchetypeContent]
    locations: dict[str, LocationContent]
