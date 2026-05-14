"""Trait Card generation agent."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.game.agents.islander_voice import load_dotenv_local
from src.game.content.archetype_templates import ARCHETYPE_TEMPLATES, ArchetypeTemplate
from src.game.content.trait_library import opening_trait_cards
from src.game.state.models import Gender, IslanderState
from src.game.state.traits import CORE_TRAIT_KEYS, PersonaSummary, TraitCard, TraitFact

TRAIT_GENERATOR_MODEL = "gpt-5.4-mini"


@dataclass(frozen=True)
class GenerationSeed:
    """One deterministic slot fed to the Trait Generator."""

    slot_id: str
    name: str
    archetype_id: str
    template: ArchetypeTemplate
    gender: Gender
    age_band: tuple[int, int]
    big5: tuple[int, int, int, int, int]
    used_secret_engines: tuple[str, ...] = ()


class TraitCardBatch(BaseModel):
    """Structured Trait Generator output."""

    model_config = ConfigDict(extra="forbid")

    cast: dict[str, TraitCard] = Field(min_length=1)


class OpenAITraitGenerator:
    """Persona-first Trait Card generator backed by OpenAI Responses."""

    def __init__(self, *, model: str = TRAIT_GENERATOR_MODEL) -> None:
        load_dotenv_local()
        self._model = model

    @cached_property
    def _client(self) -> OpenAI:
        return OpenAI()

    def generate_opening_cast(self, seeds: Iterable[GenerationSeed]) -> dict[str, TraitCard]:
        """Generate and validate opening Trait Cards."""
        seed_list = list(seeds)
        rendered = _render_seeds(seed_list)
        last_error: Exception | None = None
        for attempt in range(2):
            input_text = rendered
            if last_error is not None:
                input_text = (
                    f"{rendered}\n\nPrevious output failed validation: {last_error}. "
                    "Return corrected JSON only. Every Heartbreaker needs exactly the core_traits shape "
                    "and 6-10 concrete flavor_traits."
                )
            response = self._client.responses.create(
                model=self._model,
                reasoning={"effort": "low"},
                instructions=Path("src/game/agents/prompts/trait_generator.md").read_text(encoding="utf-8"),
                input=input_text,
                text={"format": {"type": "json_object"}},
                max_output_tokens=12000,
            )
            try:
                parsed = _parse_trait_batch(response.output_text)
                validate_trait_cards(parsed.cast)
                return parsed.cast
            except (ValueError, ValidationError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt == 1:
                    raise
        raise AssertionError("unreachable trait generator retry state")


def mock_opening_trait_cards() -> dict[str, TraitCard]:
    """Return deterministic curated opening cards."""
    return opening_trait_cards()


def assign_trait_cards(islanders: list[IslanderState], trait_cards: dict[str, TraitCard]) -> None:
    """Attach Trait Cards and persona backstory to matching islanders."""
    for islander in islanders:
        card = trait_cards.get(islander.id)
        if card is None:
            continue
        islander.trait_card = card
        islander.backstory = card.persona.history


def opening_generation_seeds(islanders: list[IslanderState]) -> list[GenerationSeed]:
    """Build deterministic generation seeds from starting islanders."""
    used: list[str] = []
    seeds: list[GenerationSeed] = []
    for islander in islanders:
        template = ARCHETYPE_TEMPLATES.get(islander.archetype, ARCHETYPE_TEMPLATES["friend"])
        seeds.append(
            GenerationSeed(
                slot_id=islander.id,
                name=islander.name,
                archetype_id=template.id,
                template=template,
                gender=islander.gender,
                age_band=(24, 31),
                big5=(
                    islander.big5.openness,
                    islander.big5.conscientiousness,
                    islander.big5.extraversion,
                    islander.big5.agreeableness,
                    islander.big5.neuroticism,
                ),
                used_secret_engines=tuple(used),
            )
        )
        used.extend(template.typical_secret_engines[:1])
    return seeds


def validate_trait_cards(cards: dict[str, TraitCard]) -> None:
    """Fail loud when generated Trait Cards violate core constraints."""
    engines: set[str] = set()
    for slot_id, card in cards.items():
        missing = CORE_TRAIT_KEYS - set(card.core_traits)
        if missing:
            raise ValueError(f"TraitCard {slot_id} missing core traits: {sorted(missing)}")
        engine = card.persona.secret_engine.strip().lower()
        if not engine or engine in engines:
            raise ValueError(f"duplicate or empty secret_engine for {slot_id}")
        engines.add(engine)
        for key in CORE_TRAIT_KEYS:
            fact = card.core_traits[key]
            if fact.key != key:
                raise ValueError(f"TraitCard {slot_id}.{key} has mismatched key {fact.key!r}")
            if key == "hidden_secret" and fact.tier != 4:
                raise ValueError(f"TraitCard {slot_id}.hidden_secret must be tier four")
        if not 6 <= len(card.flavor_traits) <= 10:
            raise ValueError(f"TraitCard {slot_id} must have 6-10 flavor traits")


def _parse_trait_batch(output_text: str) -> TraitCardBatch:
    """Parse canonical TraitCard JSON, accepting one common flat output shape."""
    try:
        return TraitCardBatch.model_validate_json(output_text)
    except ValidationError:
        raw = json.loads(output_text)
        if not isinstance(raw, dict) or not isinstance(raw.get("cast"), dict):
            raise
        return TraitCardBatch(
            cast={
                slot_id: _coerce_trait_card(entry)
                for slot_id, entry in raw["cast"].items()
                if isinstance(entry, dict)
            }
        )


def _coerce_trait_card(entry: dict[str, object]) -> TraitCard:
    if "persona" in entry and "core_traits" in entry:
        try:
            return TraitCard.model_validate(entry)
        except ValidationError:
            core_source = entry.get("core_traits")
            flavor_source = entry.get("flavor_traits")
            core = core_source if isinstance(core_source, dict) else entry
            core_traits = {key: _coerce_trait_fact(key, core.get(key)) for key in sorted(CORE_TRAIT_KEYS)}
            persona = _coerce_persona(entry.get("persona"), fallback_secret=_fallback_secret(core_traits))
            return TraitCard(
                persona=persona,
                core_traits=core_traits,
                flavor_traits=_coerce_flavor_traits(flavor_source),
            )
    core_traits = {key: _coerce_trait_fact(key, entry.get(key)) for key in sorted(CORE_TRAIT_KEYS)}
    persona = _coerce_persona(entry, fallback_secret=_fallback_secret(core_traits))
    return TraitCard(
        persona=persona,
        core_traits=core_traits,
        flavor_traits=_coerce_flavor_traits(entry.get("flavor_traits")),
    )


def _coerce_persona(raw: object, *, fallback_secret: str) -> PersonaSummary:
    if isinstance(raw, str):
        return PersonaSummary(
            one_line=raw,
            voice_notes=raw,
            history=raw,
            contradictions=[],
            secret_engine=_secret_from_text(raw, fallback_secret),
        )
    entry = raw if isinstance(raw, dict) else {}
    summary = str(entry.get("summary") or entry.get("persona_summary") or entry.get("one_line") or "A layered Heartbreaker.")
    raw_contradictions = entry.get("contradictions", [])
    contradictions = [str(item) for item in raw_contradictions] if isinstance(raw_contradictions, list) else []
    return PersonaSummary(
        one_line=summary,
        voice_notes=str(entry.get("voice_notes") or summary),
        history=str(entry.get("history") or summary),
        contradictions=contradictions,
        secret_engine=str(entry.get("secret_engine") or _secret_from_text(summary, fallback_secret)),
    )


def _coerce_trait_fact(key: str, raw: object) -> TraitFact:
    value = raw
    distractors: list[str] = []
    if isinstance(raw, dict):
        value = raw.get("value", "")
        raw_distractors = raw.get("distractors", [])
        if not raw_distractors and raw.get("distractor") is not None:
            raw_distractors = [raw.get("distractor")]
        if isinstance(raw_distractors, list):
            distractors = [str(item) for item in raw_distractors]
    return TraitFact(
        key=key,
        value=str(value or "unknown"),
        distractors=distractors,
        tier=_tier_for_core_key(key),
        mechanical=True,
    )


def _coerce_flavor_traits(raw: object) -> dict[str, TraitFact]:
    if isinstance(raw, list):
        raw = {
            str(item.get("key")): item
            for item in raw
            if isinstance(item, dict) and item.get("key")
        }
    if not isinstance(raw, dict):
        return {}
    traits: dict[str, TraitFact] = {}
    for key, value in raw.items():
        traits[str(key)] = _coerce_trait_fact(str(key), value).model_copy(
            update={"tier": 0, "mechanical": False}
        )
    return traits


def _fallback_secret(core_traits: dict[str, TraitFact]) -> str:
    insecurity = core_traits.get("insecurity")
    hidden = core_traits.get("hidden_secret")
    parts = [fact.value for fact in (insecurity, hidden) if fact is not None and fact.value != "unknown"]
    return "; ".join(parts) or "hidden motive not specified"


def _secret_from_text(text: str, fallback: str) -> str:
    marker = "secret_engine is that "
    lower = text.lower()
    if marker in lower:
        start = lower.index(marker) + len(marker)
        end = text.find(".", start)
        return text[start:end if end != -1 else None].strip()
    return fallback


def _tier_for_core_key(key: str) -> int:
    if key in {"occupation", "hometown", "age"}:
        return 1
    if key in {"favorite_food", "hobby", "drink_of_choice"}:
        return 2
    if key in {"biggest_fear", "love_language", "worst_habit", "pet_peeve"}:
        return 3
    return 4


def _render_seeds(seeds: list[GenerationSeed]) -> str:
    lines = ["Generate JSON Trait Cards for these Heartbreakers:"]
    for seed in seeds:
        lines.extend(
            [
                f"- slot_id: {seed.slot_id}",
                f"  name: {seed.name}",
                f"  archetype: {seed.archetype_id}",
                f"  gender: {seed.gender.value}",
                f"  age_band: {seed.age_band[0]}-{seed.age_band[1]}",
                "  big5: "
                f"openness {seed.big5[0]}, conscientiousness {seed.big5[1]}, "
                f"extraversion {seed.big5[2]}, agreeableness {seed.big5[3]}, "
                f"neuroticism {seed.big5[4]}",
                f"  template_secret_engines: {', '.join(seed.template.typical_secret_engines)}",
                f"  already_used_secret_engines: {', '.join(seed.used_secret_engines) or 'none'}",
            ]
        )
    return "\n".join(lines)
