"""Typed player-facing Daily Recap projection contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.game.engine.daily_recap import humanize_player_reference
from src.game.engine.state_access import display_name
from src.game.state.memory import RecapDisposition
from src.game.state.models import DailyRecap, GameState

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


_RESORT_LABELS = {
    "main": "Sunset Bay",
    "flush_of_hearts": "Flush of Hearts",
}


def project_daily_recap(state: GameState, recap: DailyRecap) -> DailyRecapView:
    """Project canonical recap facts into the sole player-facing shape."""
    return DailyRecapView(
        day=recap.day,
        resort_id=recap.resort_id.value,
        resort_label=_RESORT_LABELS[recap.resort_id.value],
        items=[
            DailyRecapItemView(
                section=_section(item.recap_disposition),
                speaker_label=(
                    "You"
                    if item.holder_id == state.player.id
                    else display_name(state, item.holder_id)
                ),
                content=humanize_player_reference(item.content),
                emphasis="strong" if item.emotional_weight >= 7 else "standard",
            )
            for item in recap.items
        ],
    )


def _section(disposition: RecapDisposition) -> RecapSection:
    if disposition is RecapDisposition.YOUR_DAY:
        return "your_day"
    if disposition is RecapDisposition.WHILE_BUSY:
        return "while_busy"
    raise ValueError("Daily Recap item cannot use the none disposition")
