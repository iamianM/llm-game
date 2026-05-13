"""Review bookmark models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

BookmarkCategory = Literal["event", "highlight", "anomaly", "error", "note"]


class Bookmark(BaseModel):
    """One review bookmark attached to a trace turn."""

    model_config = ConfigDict(extra="forbid")

    turn: int
    kind: str
    category: BookmarkCategory
    title: str
    note: str = ""
    scene_id: str | None = None
