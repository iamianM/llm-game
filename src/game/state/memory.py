"""Canonical memory models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Memory(BaseModel):
    """One fact remembered by the player or an islander."""

    model_config = ConfigDict(extra="forbid")

    id: str
    holder_id: str
    subject_id: str
    content: str
    source: Literal["direct", "witnessed", "told_by"]
    source_id: str | None = None
    formed_on_day: int
    formed_on_turn: int
    emotional_weight: int = Field(ge=1, le=10)
    tags: list[str] = Field(default_factory=list)
    durable: bool = True


class MemoryDraft(BaseModel):
    """One agent-authored memory before deterministic id assignment."""

    model_config = ConfigDict(extra="forbid")

    holder_id: str
    subject_id: str
    content: str
    source: Literal["direct", "witnessed", "told_by"]
    source_id: str | None = None
    emotional_weight: int = Field(ge=1, le=10)
    tags: list[str] = Field(default_factory=list)
    durable: bool = True


class MemoryBatch(BaseModel):
    """A typed curator commit containing durable memories."""

    model_config = ConfigDict(extra="forbid")

    memories: list[MemoryDraft] = Field(min_length=1, max_length=8)
