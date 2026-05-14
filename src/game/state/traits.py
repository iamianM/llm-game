"""Structured trait cards and knowledge state."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CORE_TRAIT_KEYS = {
    "occupation",
    "hometown",
    "age",
    "favorite_food",
    "hobby",
    "drink_of_choice",
    "biggest_fear",
    "love_language",
    "worst_habit",
    "pet_peeve",
    "insecurity",
    "past_heartbreak",
    "hidden_secret",
}

TIER_THRESHOLDS = {1: 0, 2: 25, 3: 50, 4: 75}


class PersonaSummary(BaseModel):
    """Internal narrative core for one Heartbreaker."""

    model_config = ConfigDict(extra="forbid")

    one_line: str
    voice_notes: str
    history: str
    contradictions: list[str] = Field(default_factory=list)
    secret_engine: str


class TraitFact(BaseModel):
    """One true fact about a Heartbreaker."""

    model_config = ConfigDict(extra="forbid")

    key: str
    value: str
    distractors: list[str] = Field(default_factory=list)
    tier: int = Field(default=0, ge=0, le=4)
    reveal_tags: list[str] = Field(default_factory=list)
    mechanical: bool = True


class TraitCard(BaseModel):
    """Full internal truth card for one Heartbreaker."""

    model_config = ConfigDict(extra="forbid")

    persona: PersonaSummary
    core_traits: dict[str, TraitFact]
    flavor_traits: dict[str, TraitFact] = Field(default_factory=dict)


class KnownFact(BaseModel):
    """One fact or belief known by the player or an NPC."""

    model_config = ConfigDict(extra="forbid")

    fact_key: str
    value: str
    source: Literal["direct", "social_event", "gossip", "witnessed"]
    source_npc_id: str | None = None
    learned_on_day: int
    learned_on_turn: int
    confidence: float = Field(ge=0.0, le=1.0)
    citation: str


KnownFacts = dict[str, KnownFact]


def empty_trait_card() -> TraitCard:
    """Return a placeholder card used only before content assignment."""
    return TraitCard(
        persona=PersonaSummary(
            one_line="Unassigned Heartbreaker.",
            voice_notes="Unassigned.",
            history="Unassigned.",
            contradictions=[],
            secret_engine="unassigned",
        ),
        core_traits={
            key: TraitFact(
                key=key,
                value="unknown",
                tier=_tier_for_core_key(key),
                mechanical=True,
            )
            for key in CORE_TRAIT_KEYS
        },
    )


def _tier_for_core_key(key: str) -> int:
    if key in {"occupation", "hometown", "age"}:
        return 1
    if key in {"favorite_food", "hobby", "drink_of_choice"}:
        return 2
    if key in {"biggest_fear", "love_language", "worst_habit", "pet_peeve"}:
        return 3
    return 4
