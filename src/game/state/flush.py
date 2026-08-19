"""Flush of Hearts state models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ResortName(StrEnum):
    MAIN = "main"
    FLUSH_OF_HEARTS = "flush_of_hearts"


class FlushDecision(StrEnum):
    RETURN_WITH_ORIGINAL = "return_with_original"
    RETURN_WITH_NEW = "return_with_new"
    RETURN_SINGLE = "return_single"


class FlushOfHeartsState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    started_on_day: int
    return_day: int = 6
    original_partner_id: str | None = None
    flush_heartbreaker_ids: list[str] = Field(default_factory=list)
    sunset_bay_partner_ids: list[str] = Field(default_factory=list)
    player_decision: FlushDecision | None = None
    chosen_partner_id: str | None = None
    returned: bool = False
    partners_swapped: bool = False
    player_perception_before: int
    player_perception_after: int | None = None
