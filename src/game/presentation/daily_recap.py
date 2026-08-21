"""Typed player-facing Daily Recap projection contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RecapSection = Literal["your_day", "while_busy"]
RecapEmphasis = Literal["standard", "strong"]


class DailyRecapItemView(BaseModel):
    """One display-safe recap item."""

    model_config = ConfigDict(extra="forbid")

    section: RecapSection
    speaker_label: str
    content: str
    emphasis: RecapEmphasis


class DailyRecapView(BaseModel):
    """One complete player-facing recap."""

    model_config = ConfigDict(extra="forbid")

    day: int = Field(ge=1)
    resort_id: str
    resort_label: str
    items: list[DailyRecapItemView] = Field(default_factory=list, max_length=5)
