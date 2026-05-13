"""Phase clock state."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PhaseClock(BaseModel):
    """Minute budget for the current day phase."""

    model_config = ConfigDict(extra="forbid")

    phase: str
    budget_minutes: int = Field(ge=0)
    elapsed_minutes: int = Field(default=0, ge=0)

    @property
    def remaining(self) -> int:
        return max(0, self.budget_minutes - self.elapsed_minutes)

    @property
    def expired(self) -> bool:
        return self.elapsed_minutes >= self.budget_minutes
