"""Trait Card generation agent."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from src.game.agents.islander_voice import load_dotenv_local
from src.game.agents.runtime import (
    GAME_AGENT_MODEL,
    begin_agent_attempt,
    end_agent_attempt,
    mark_agent_trace_validation_error,
    reasoning_request_kwargs,
    record_agent_trace,
)
from src.game.content.archetype_templates import ARCHETYPE_TEMPLATES, ArchetypeTemplate
from src.game.content.trait_library import opening_trait_cards
from src.game.state.models import Gender, IslanderState
from src.game.state.traits import CORE_TRAIT_KEYS, PersonaSummary, TraitCard, TraitFact

TRAIT_GENERATOR_MODEL = GAME_AGENT_MODEL
# Trait generation is creative-structured output, not deep reasoning. Default
# to a lower reasoning effort than the other agents (which default to "high")
# so the boot path runs in seconds, not minutes. Overridable via env var.
TRAIT_GENERATOR_REASONING_EFFORT = os.environ.get(
    "LLM_TRAIT_GENERATOR_REASONING_EFFORT", "low"
)
# Max parallel single-islander LLM calls during opening cast generation.
TRAIT_GENERATOR_MAX_CONCURRENCY = int(
    os.environ.get("LLM_TRAIT_GENERATOR_MAX_CONCURRENCY", "8")
)
# Repo-relative identifier used in trace records (stable across hosts).
TRAIT_GENERATOR_PROMPT = "src/game/agents/prompts/trait_generator.md"
# Filesystem path resolved relative to this module so the prompt opens
# regardless of process cwd (Vercel runs lambdas from /var/task; local
# CLI runs from the repo root).
_TRAIT_GENERATOR_PROMPT_FILE = Path(__file__).parent / "prompts" / "trait_generator.md"


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
    assigned_secret_engine: str | None = None


class GeneratedTraitCard(TraitCard):
    """Trait Card shape required from the live generator."""

    flavor_traits: dict[str, TraitFact]

    @field_validator("flavor_traits")
    @classmethod
    def _validate_flavor_trait_count(cls, value: dict[str, TraitFact]) -> dict[str, TraitFact]:
        if not 6 <= len(value) <= 10:
            raise ValueError("flavor_traits must contain 6-10 concrete traits")
        return value


class TraitCardBatch(BaseModel):
    """Structured Trait Generator output."""

    model_config = ConfigDict(extra="forbid")

    cast: dict[str, GeneratedTraitCard]

    @field_validator("cast")
    @classmethod
    def _validate_cast_count(cls, value: dict[str, GeneratedTraitCard]) -> dict[str, GeneratedTraitCard]:
        if not value:
            raise ValueError("cast must contain at least one Trait Card")
        return value


class OpenAITraitGenerator:
    """Persona-first Trait Card generator backed by OpenAI Responses."""

    def __init__(self, *, model: str = TRAIT_GENERATOR_MODEL) -> None:
        load_dotenv_local()
        self._model = model

    @cached_property
    def _client(self) -> OpenAI:
        return OpenAI()

    def generate_opening_cast(self, seeds: Iterable[GenerationSeed]) -> dict[str, TraitCard]:
        """Generate and validate opening Trait Cards.

        Each seed becomes its own parallel single-islander LLM call (the
        opening cast is eight Heartbreakers — a single batched request used
        to take ~5 minutes at high reasoning effort, which was the entire
        boot wait). Secret-engine uniqueness is pre-claimed by assigning each
        seed a specific entry from its archetype's `typical_secret_engines`
        pool, so concurrent calls don't need to coordinate to avoid duplicates.

        Per-call retries handle transient parse failures locally; only a
        permanently failing call propagates out.
        """
        seed_list = _claim_secret_engines(list(seeds))
        if not seed_list:
            return {}
        max_workers = max(1, min(len(seed_list), TRAIT_GENERATOR_MAX_CONCURRENCY))
        cards: dict[str, TraitCard] = {}
        errors: list[BaseException] = []
        instructions = _TRAIT_GENERATOR_PROMPT_FILE.read_text(encoding="utf-8")
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self._generate_one_with_retries, seed, instructions): seed
                for seed in seed_list
            }
            for future in as_completed(futures):
                seed = futures[future]
                try:
                    cards[seed.slot_id] = future.result()
                except BaseException as exc:  # noqa: BLE001 — re-raise after collecting
                    errors.append(exc)
        if errors:
            raise errors[0]
        validate_trait_cards(cards)
        return cards

    def _generate_one_with_retries(
        self, seed: GenerationSeed, instructions: str
    ) -> TraitCard:
        """Generate one Trait Card with three local retries on validation failure."""
        rendered = _render_seeds([seed])
        last_error: Exception | None = None
        for attempt in range(3):
            attempt_number = attempt + 1
            input_text = rendered
            if last_error is not None:
                input_text = (
                    f"{rendered}\n\nPrevious output failed validation: {last_error}. "
                    "Return corrected JSON only. The cast must contain exactly one "
                    f"entry keyed by `{seed.slot_id}` with the required core_traits "
                    "shape and 6-10 concrete flavor_traits."
                )
            try:
                parsed = self._generate_batch(input_text, attempt_number, instructions)
                if seed.slot_id not in parsed.cast:
                    raise ValueError(
                        f"single-card response missing slot_id {seed.slot_id!r}; "
                        f"got {sorted(parsed.cast.keys())}"
                    )
                return parsed.cast[seed.slot_id]
            except (ValueError, ValidationError, json.JSONDecodeError) as exc:
                mark_agent_trace_validation_error("trait_generator", attempt_number, exc)
                last_error = exc
                if attempt == 2:
                    raise
        raise AssertionError("unreachable trait generator retry state")

    def _generate_batch(
        self, input_text: str, attempt_number: int, instructions: str | None = None
    ) -> TraitCardBatch:
        """Request one parsed Trait Card batch from the model."""
        attempt_token = begin_agent_attempt(attempt_number)
        if instructions is None:
            instructions = _TRAIT_GENERATOR_PROMPT_FILE.read_text(encoding="utf-8")
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=instructions,
                input=input_text,
                text={"format": {"type": "json_object"}},
                **reasoning_request_kwargs(effort=TRAIT_GENERATOR_REASONING_EFFORT),
            )
        finally:
            end_agent_attempt(attempt_token)
        record_agent_trace(
            agent_name="trait_generator",
            model=self._model,
            prompt_path=TRAIT_GENERATOR_PROMPT,
            response=response,
            output=response.output_text,
        )
        return _parse_trait_batch(response.output_text)


def mock_opening_trait_cards() -> dict[str, TraitCard]:
    """Return deterministic curated opening cards."""
    return opening_trait_cards()


# Trailing performance descriptors that the low-reasoning model sometimes
# tacks onto otherwise-clean trait values. Stripped before the values
# appear as multiple-choice quiz options so cards read as parallel nouns
# instead of half-sentences. The patterns match a leading space + the
# descriptor anywhere at the end of the value.
import re as _re
_VALUE_TRAIL_PATTERNS: tuple[_re.Pattern[str], ...] = (
    _re.compile(r"\s+(?:every time|every single time|each time)\.?$", _re.IGNORECASE),
    _re.compile(r"\s+(?:always|deliberately|on purpose|absolutely|honestly)\.?$", _re.IGNORECASE),
    _re.compile(r"\s+(?:for hours|for ages|all night|all day|all the time)\.?$", _re.IGNORECASE),
    _re.compile(
        r"\s+when\s+(?:no\s+one|nobody|she|he|they|everyone\s+else|the\s+camera|nobody'?s?)\s+(?:is\s+)?(?:looking|watching|home|asleep|around|alone|sleeps)\.?$",
        _re.IGNORECASE,
    ),
    _re.compile(r"\s+(?:sung|sang|played|performed)\s+\w[\w\s]*\.?$", _re.IGNORECASE),
    _re.compile(r"\s+with improvised crowd work\.?$", _re.IGNORECASE),
    _re.compile(r"\s+deliberately\s+\w[\w\s]*\.?$", _re.IGNORECASE),
    _re.compile(r"\s+half a beat\s+(?:late|early|behind)\.?$", _re.IGNORECASE),
    _re.compile(r"\s+a beat (?:late|early)\.?$", _re.IGNORECASE),
    # "X too much/often/loudly" trailing modifier on otherwise-OK noun.
    # Combines the optional "that" relative connector so "westerns that he
    # repeats too much" -> "westerns" in one pass.
    _re.compile(
        r"\s+(?:that\s+)?(?:he|she|they|him|her|them|i)\s+\w[\w\s']*?\s+too\s+(?:much|often|loudly)\.?$",
        _re.IGNORECASE,
    ),
    # "X that he/she does Y" relative clause trailing onto a noun.
    _re.compile(r"\s+that\s+(?:he|she|they)\s+\w[\w\s']*\.?$", _re.IGNORECASE),
)


def _clean_trait_value(value: str) -> str:
    """Strip trailing performance descriptors from a trait value."""
    cleaned = value.strip()
    for _ in range(4):  # apply repeatedly so chained trails are all stripped
        prev = cleaned
        for pattern in _VALUE_TRAIL_PATTERNS:
            cleaned = pattern.sub("", cleaned).strip()
        if cleaned == prev:
            break
    return cleaned or value.strip()


def _polish_trait_cards(cards: dict[str, TraitCard]) -> None:
    """Clean values + auto-fill distractors from peer islanders.

    Runs after the model has produced its raw Trait Cards. Two passes:
    (1) trim trailing performance descriptors off every value so quiz
    cards read as parallel nouns ("Stay by Rihanna", not "Stay by
    Rihanna every time"); (2) for any flavor trait whose distractors are
    empty, pick three peer islanders' cleaned values for the same key as
    plausible wrong answers — the quiz selector already does this as a
    fallback, but doing it here makes the saved Trait Card display-ready.
    """
    for card in cards.values():
        for fact in card.core_traits.values():
            fact.value = _clean_trait_value(fact.value)
            fact.distractors = [_clean_trait_value(d) for d in fact.distractors]
        for fact in card.flavor_traits.values():
            fact.value = _clean_trait_value(fact.value)
            fact.distractors = [_clean_trait_value(d) for d in fact.distractors]
    # Build a peer-value index keyed by flavor trait key so we can backfill.
    peer_values: dict[str, list[str]] = {}
    for card in cards.values():
        for key, fact in card.flavor_traits.items():
            peer_values.setdefault(key, []).append(fact.value)
    for card in cards.values():
        for key, fact in card.flavor_traits.items():
            if len(fact.distractors) >= 3:
                continue
            seen = {fact.value, *fact.distractors}
            for peer in peer_values.get(key, []):
                if peer in seen or not peer:
                    continue
                fact.distractors.append(peer)
                seen.add(peer)
                if len(fact.distractors) >= 3:
                    break


def assign_trait_cards(islanders: list[IslanderState], trait_cards: dict[str, TraitCard]) -> None:
    """Attach Trait Cards and persona backstory to matching islanders."""
    _polish_trait_cards(trait_cards)
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


def _coerce_trait_card(entry: dict[str, object]) -> GeneratedTraitCard:
    if "persona" in entry and "core_traits" in entry:
        try:
            return GeneratedTraitCard.model_validate(entry)
        except ValidationError:
            core_source = entry.get("core_traits")
            flavor_source = entry.get("flavor_traits")
            core = core_source if isinstance(core_source, dict) else entry
            core_traits = {key: _coerce_trait_fact(key, core.get(key)) for key in sorted(CORE_TRAIT_KEYS)}
            persona = _coerce_persona(entry.get("persona"), fallback_secret=_fallback_secret(core_traits))
            return GeneratedTraitCard(
                persona=persona,
                core_traits=core_traits,
                flavor_traits=_coerce_flavor_traits(flavor_source),
            )
    core_traits = {key: _coerce_trait_fact(key, entry.get(key)) for key in sorted(CORE_TRAIT_KEYS)}
    persona = _coerce_persona(entry, fallback_secret=_fallback_secret(core_traits))
    return GeneratedTraitCard(
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


def _claim_secret_engines(seeds: list[GenerationSeed]) -> list[GenerationSeed]:
    """Pre-assign each seed a unique secret_engine from its archetype pool.

    Lets the opening cast run as parallel single-islander calls without the
    calls needing to coordinate to avoid duplicate engines. Walks the input
    order so two islanders sharing an archetype get the archetype's first
    two engines; if the pool is exhausted the seed keeps whatever the model
    invents (validate_trait_cards still enforces overall uniqueness).
    """
    used_by_archetype: dict[str, set[str]] = {}
    claimed: list[GenerationSeed] = []
    for seed in seeds:
        pool = list(seed.template.typical_secret_engines)
        used = used_by_archetype.setdefault(seed.archetype_id, set())
        choice = next((engine for engine in pool if engine not in used), None)
        if choice is None:
            claimed.append(seed)
            continue
        used.add(choice)
        claimed.append(
            type(seed)(
                slot_id=seed.slot_id,
                name=seed.name,
                archetype_id=seed.archetype_id,
                template=seed.template,
                gender=seed.gender,
                age_band=seed.age_band,
                big5=seed.big5,
                used_secret_engines=seed.used_secret_engines,
                assigned_secret_engine=choice,
            )
        )
    return claimed


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
        if seed.assigned_secret_engine is not None:
            lines.append(
                f"  REQUIRED secret_engine for this card: {seed.assigned_secret_engine}"
            )
    return "\n".join(lines)
