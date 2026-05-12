"""Tiered conversation intents.

Design sources:
- 05-Interaction-System.md: Hybrid Menu System
- 02-Core-Mechanics.md: Interaction Success Formula
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.game.state.models import GameState, IslanderState, RelationshipDelta


class IntentCategory(StrEnum):
    """Top-level conversation intent categories."""

    FRIENDLY = "friendly"
    FLIRTY = "flirty"
    DEEP = "deep"
    BANTER = "banter"
    SUPPORTIVE = "supportive"
    GOSSIP = "gossip"


Risk = Literal["safe", "low", "medium", "high"]


CATEGORY_DEFAULT_RISK: dict[IntentCategory, Risk] = {
    IntentCategory.FRIENDLY: "low",
    IntentCategory.BANTER: "low",
    IntentCategory.FLIRTY: "medium",
    IntentCategory.DEEP: "high",
    IntentCategory.SUPPORTIVE: "safe",
    IntentCategory.GOSSIP: "medium",
}


class IntentDeltaTable(BaseModel):
    """Success and miss deltas for an intent."""

    model_config = ConfigDict(extra="forbid")

    success: RelationshipDelta
    miss: RelationshipDelta


class Intent(BaseModel):
    """One structured conversation intent."""

    model_config = ConfigDict(extra="forbid")

    id: str
    category: IntentCategory
    label: str
    stat_used: str
    tags: list[str] = Field(default_factory=list)
    unlock_affection: int = Field(ge=0, le=100)
    risk: Risk | None = None
    relationship_deltas: IntentDeltaTable


class IntentCatalog(BaseModel):
    """Loaded intent catalog."""

    model_config = ConfigDict(extra="forbid")

    intents: list[Intent]


@lru_cache(maxsize=8)
def load_intents(path: Path = Path("content/intents.yaml")) -> list[Intent]:
    """Load and validate the intent catalog."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("intent catalog must be a mapping")
    return IntentCatalog.model_validate(cast(dict[str, object], raw)).intents


def get_intent(intent_id: str) -> Intent:
    """Return one intent by id."""
    for intent in load_intents():
        if intent.id == intent_id:
            return intent
    raise ValueError(f"unknown intent_id: {intent_id}")


def available_intents_for(state: GameState, target_id: str) -> list[Intent]:
    """Return unlocked intents for a visible target."""
    target = _find_visible_target(state, target_id)
    affection = target.relationship.affection
    return [intent for intent in load_intents() if affection >= intent.unlock_affection]


def effective_risk(intent: Intent) -> Risk:
    """Return explicit intent risk or the category default."""
    return intent.risk or CATEGORY_DEFAULT_RISK[intent.category]


def _find_visible_target(state: GameState, target_id: str) -> IslanderState:
    for islander in state.islanders:
        if (
            islander.id == target_id
            and not islander.eliminated
            and islander.location_id == state.location_id
        ):
            return islander
    raise ValueError(f"target is not visible: {target_id}")
