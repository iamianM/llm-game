"""Load curated Trait Cards for deterministic mock runs."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.game.state.traits import CORE_TRAIT_KEYS, TraitCard, TraitFact


class CuratedCastEntry(BaseModel):
    """One curated Heartbreaker entry."""

    model_config = ConfigDict(extra="allow")

    slot_id: str
    name: str
    archetype: str
    gender: str
    age: int
    persona: dict[str, Any]
    core_traits: dict[str, dict[str, Any]]
    flavor_traits: dict[str, dict[str, Any]] = {}


class CuratedCast(BaseModel):
    """Curated cast content file."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int
    opening_cast: list[CuratedCastEntry]
    heart_throb_pool: list[CuratedCastEntry]


@lru_cache(maxsize=1)
def load_curated_cast(path: Path = Path("src/game/content/curated_cast.json")) -> CuratedCast:
    """Load and validate curated Trait Card content."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    cast = CuratedCast.model_validate(raw)
    for entry in [*cast.opening_cast, *cast.heart_throb_pool]:
        card = trait_card_from_entry(entry)
        missing = CORE_TRAIT_KEYS - set(card.core_traits)
        if missing:
            raise ValueError(f"curated TraitCard for {entry.slot_id} missing core traits: {sorted(missing)}")
    return cast


def opening_trait_cards() -> dict[str, TraitCard]:
    """Return opening cast Trait Cards keyed by slot id."""
    return {entry.slot_id: trait_card_from_entry(entry) for entry in load_curated_cast().opening_cast}


def heart_throb_trait_cards() -> dict[str, TraitCard]:
    """Return Heart Throb Trait Cards keyed by slot id."""
    return {entry.slot_id: trait_card_from_entry(entry) for entry in load_curated_cast().heart_throb_pool}


def trait_card_from_entry(entry: CuratedCastEntry) -> TraitCard:
    """Convert one curated JSON entry into canonical model objects."""
    core_traits = {
        key: _fact(key, payload, mechanical=True)
        for key, payload in entry.core_traits.items()
    }
    flavor_traits = {
        key: _fact(key, payload, mechanical=False)
        for key, payload in entry.flavor_traits.items()
    }
    return TraitCard.model_validate(
        {
            "persona": entry.persona,
            "core_traits": core_traits,
            "flavor_traits": flavor_traits,
        }
    )


def _fact(key: str, payload: dict[str, Any], *, mechanical: bool) -> TraitFact:
    data = dict(payload)
    data.setdefault("key", key)
    data.setdefault("mechanical", mechanical)
    data.setdefault("distractors", [])
    data.setdefault("reveal_tags", [])
    return TraitFact.model_validate(data)
