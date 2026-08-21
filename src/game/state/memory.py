"""Canonical memory models."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RecapDisposition(StrEnum):
    """Whether and where a memory may appear in the Daily Recap."""

    NONE = "none"
    YOUR_DAY = "your_day"
    WHILE_BUSY = "while_busy"


class Memory(BaseModel):
    """One fact remembered by the player or an heartbreaker."""

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
    recap_disposition: RecapDisposition
    # Cast ids (besides ``subject_id``) named in ``content``, derived
    # deterministically at the memory-creation boundary. The voice context reads
    # this structurally to whitelist natural subject echoes for the exchange
    # validator — no regex content-scan at read time. Excluded from the state
    # hash (see snapshot._strip_memory_content) because it is flavor-derived and
    # therefore LLM-nondeterministic, exactly like ``content`` itself.
    mentioned_subject_ids: list[str] = Field(default_factory=list)


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


class GossipSeed(BaseModel):
    """A curator-authored moment that can spread as gossip."""

    model_config = ConfigDict(extra="forbid")

    subject_id: str
    gist: str
    holder_id: str
    spreadable_to: list[str] = Field(default_factory=list)
    emotional_weight: int = Field(ge=1, le=10)
    tags: list[str] = Field(default_factory=list)


class MemoryBatch(BaseModel):
    """A typed curator commit containing durable memories."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["player", "background"] = "player"
    memories: list[MemoryDraft] = Field(min_length=1, max_length=16)
    summary: str = ""
    gossip_seeds: list[GossipSeed] = Field(default_factory=list)
