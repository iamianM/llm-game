"""Known Fact reveal and storage mechanics."""

from __future__ import annotations

from typing import Literal, cast

from src.game.engine.intents import Intent
from src.game.state.models import GameState, HeartbreakerState
from src.game.state.traits import TIER_THRESHOLDS, KnownFact, TraitFact


def emit_fact_reveal(
    state: GameState,
    target: HeartbreakerState,
    intent: Intent,
    *,
    source: str = "direct",
    source_npc_id: str | None = None,
    confidence: float = 1.0,
) -> KnownFact | None:
    """Reveal one eligible trait fact to the player."""
    if intent.reveal_tier <= 0:
        return None
    tier = _effective_tier(target, intent)
    if target.familiarity_with_player < TIER_THRESHOLDS[tier]:
        return None
    key, fact = pick_revealable_trait(target, tier, intent.reveal_tag, state.player.known_facts)
    if fact is None or key is None:
        return None
    known = KnownFact(
        fact_key=f"{target.id}.{key}",
        value=fact.value,
        source=cast(Literal["direct", "social_event", "gossip", "witnessed"], source),
        source_npc_id=source_npc_id,
        learned_on_day=state.day,
        learned_on_turn=state.turn_index,
        confidence=confidence,
        citation=_citation(target.name, state.day, source, source_npc_id),
    )
    state.player.known_facts[known.fact_key] = known
    return known


def emit_fact_reveal_by_tier(
    state: GameState,
    target: HeartbreakerState,
    tier: int,
    *,
    reveal_tag: str | None = None,
) -> KnownFact | None:
    """Reveal one fact by explicit tier for contextual follow-ups."""
    if tier <= 0 or target.familiarity_with_player < TIER_THRESHOLDS[tier]:
        return None
    key, fact = pick_revealable_trait(target, tier, reveal_tag, state.player.known_facts)
    if key is None or fact is None:
        return None
    known = KnownFact(
        fact_key=f"{target.id}.{key}",
        value=fact.value,
        source="direct",
        learned_on_day=state.day,
        learned_on_turn=state.turn_index,
        confidence=1.0,
        citation=_citation(target.name, state.day, "direct", None),
    )
    state.player.known_facts[known.fact_key] = known
    return known


def add_known_fact(holder: dict[str, KnownFact], known: KnownFact) -> None:
    """Store a KnownFact unless the holder already has it at higher confidence."""
    existing = holder.get(known.fact_key)
    if existing is not None and existing.confidence >= known.confidence:
        return
    holder[known.fact_key] = known


def pick_revealable_trait(
    target: HeartbreakerState,
    tier: int,
    reveal_tag: str | None,
    already_known: dict[str, KnownFact],
) -> tuple[str | None, TraitFact | None]:
    """Pick a fact from a tier without revealing duplicates."""
    if reveal_tag:
        fact = target.trait_card.core_traits.get(reveal_tag) or target.trait_card.flavor_traits.get(reveal_tag)
        if fact is not None and f"{target.id}.{reveal_tag}" not in already_known:
            return reveal_tag, fact
    candidates = [
        (key, fact)
        for key, fact in target.trait_card.core_traits.items()
        if fact.tier == tier and f"{target.id}.{key}" not in already_known
    ]
    if not candidates:
        candidates = [
            (key, fact)
            for key, fact in target.trait_card.flavor_traits.items()
            if f"{target.id}.{key}" not in already_known
        ]
    if not candidates:
        return None, None
    candidates.sort(key=lambda item: item[0])
    return candidates[0]


def reveal_intro_facts(state: GameState, target: HeartbreakerState) -> None:
    """Reveal tier-one intro facts for a target."""
    reveal_surface_facts(state, target, citation=f"{target.name} told you during Day One introductions.")


def reveal_partner_surface_facts(state: GameState, partner_id: str) -> None:
    """Reveal basic partner facts when the player forms a couple."""
    target = next((heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == partner_id), None)
    if target is None:
        return
    reveal_surface_facts(
        state,
        target,
        citation=f"You learned the basics while coupling with {target.name}.",
    )


def reveal_surface_facts(state: GameState, target: HeartbreakerState, *, citation: str) -> None:
    """Reveal tier-one facts for a target."""
    for key, fact in sorted(target.trait_card.core_traits.items()):
        if fact.tier != 1:
            continue
        fact_key = f"{target.id}.{key}"
        if fact_key in state.player.known_facts:
            continue
        state.player.known_facts[fact_key] = KnownFact(
            fact_key=fact_key,
            value=fact.value,
            source="direct",
            source_npc_id=None,
            learned_on_day=state.day,
            learned_on_turn=state.turn_index,
            confidence=1.0,
            citation=citation,
        )


def _effective_tier(target: HeartbreakerState, intent: Intent) -> int:
    tier = intent.reveal_tier
    if intent.id == "friendly_compliment_personality" and target.familiarity_with_player < 25:
        return 1
    if intent.id == "deep_share_feelings" and target.familiarity_with_player >= 70:
        return 4
    return tier


def _citation(target_name: str, day: int, source: str, source_npc_id: str | None) -> str:
    if source == "gossip":
        return f"You heard this about {target_name} from {source_npc_id or 'someone'} on Day {day}."
    return f"{target_name} told you directly on Day {day}."
