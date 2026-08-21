"""Memory-backed gossip mechanics."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.game.engine.memory import add_memory, create_memory
from src.game.state.memory import RecapDisposition
from src.game.state.models import GameState, HeartbreakerState, RelationshipDelta
from src.game.state.rng import SeededRng
from src.game.state.traits import KnownFact


@dataclass(frozen=True)
class GossipFollowUpResult:
    """Outcome of a gossip follow-up.

    ``stale`` is the single source of truth for "the offered memory no longer
    resolved, so this was a graceful no-op". The follow-up builder lifts it into
    a typed ``MechanicalResult`` anomaly so the no-op is countable in the review
    packet instead of being silently swallowed (ENGINEERING R16).
    """

    delta: RelationshipDelta = field(default_factory=RelationshipDelta)
    stale: bool = False


def apply_gossip_follow_up(
    state: GameState,
    source_id: str,
    intent_kind: str,
    success: bool,
) -> GossipFollowUpResult:
    """Apply a gossip follow-up and transfer the memory on success."""
    if intent_kind.startswith("ask_gossip:about_"):
        if success:
            share_gossip(state, source_id, intent_kind.removeprefix("ask_gossip:about_"))
        return GossipFollowUpResult(delta=RelationshipDelta(trust=2 if success else 0))
    memory_id = intent_kind.removeprefix("ask_gossip:")
    conversation = state.active_conversation
    if conversation is None:
        raise ValueError("gossip follow-up requires active conversation")
    source_memory = next(
        (memory for memory in conversation.gossip_offers if memory.id == memory_id),
        None,
    )
    if source_memory is None:
        # The offered memory is no longer resolvable (e.g. a stale menu after a
        # phase shift). Degrade to a neutral no-op rather than hard-crashing the
        # turn — a player-facing menu option must never dead-screen the game —
        # but flag it stale so the no-op is observable downstream.
        return GossipFollowUpResult(stale=True)
    if not success:
        return GossipFollowUpResult()
    add_memory(
        state,
        create_memory(
            holder_id="player",
            subject_id=source_memory.subject_id,
            source="told_by",
            source_id=source_id,
            day=state.day,
            turn=state.turn_index,
            weight=source_memory.emotional_weight,
            tags=["gossip", f"source_memory:{source_memory.id}", *source_memory.tags],
            content=source_memory.content,
            recap_disposition=RecapDisposition.YOUR_DAY,
        ),
    )
    return GossipFollowUpResult(delta=RelationshipDelta(trust=2))


def apply_share_gossip_follow_up(
    state: GameState,
    target_id: str,
    intent_kind: str,
    success: bool,
) -> GossipFollowUpResult:
    """Apply player-shared gossip and transfer the player's memory on success."""
    memory_id = intent_kind.removeprefix("share_gossip:")
    source_memory = next(
        (memory for memory in state.player.memories if memory.id == memory_id),
        None,
    )
    if source_memory is None:
        # The shareable memory is no longer in the player's memory list (e.g. a
        # stale menu carried across a phase shift). Degrade to a neutral no-op
        # rather than hard-crashing the turn — a player-facing menu option must
        # never dead-screen the game — but flag it stale so the no-op is observable
        # downstream (ENGINEERING R16).
        return GossipFollowUpResult(stale=True)
    if not success:
        # The share landed badly, but the player *did* say it. Record a lighter
        # "unconvinced" memory on the target so the same gossip is not re-offered
        # in the menu — otherwise it loops forever and the NPC reacts as if hearing
        # it fresh every time. The reduced weight + gossip_unconvinced tag mark that
        # the target did not buy it, so it does not propagate like believed gossip.
        add_memory(
            state,
            create_memory(
                holder_id=target_id,
                subject_id=source_memory.subject_id,
                source="told_by",
                source_id="player",
                day=state.day,
                turn=state.turn_index,
                weight=max(2, source_memory.emotional_weight - 3),
                tags=["gossip", "gossip_unconvinced", f"source_memory:{source_memory.id}"],
                content=source_memory.content,
                recap_disposition=RecapDisposition.YOUR_DAY,
            ),
        )
        return GossipFollowUpResult(delta=RelationshipDelta(trust=-1))
    add_memory(
        state,
        create_memory(
            holder_id=target_id,
            subject_id=source_memory.subject_id,
            source="told_by",
            source_id="player",
            day=state.day,
            turn=state.turn_index,
            weight=source_memory.emotional_weight,
            tags=["gossip", f"source_memory:{source_memory.id}", *source_memory.tags],
            content=source_memory.content,
            recap_disposition=RecapDisposition.YOUR_DAY,
        ),
    )
    return GossipFollowUpResult(delta=RelationshipDelta(trust=1, friendship=1))


def share_gossip(state: GameState, speaker_id: str, subject_id: str) -> KnownFact | None:
    """Transfer one known fact from speaker to player with possible distortion."""
    speaker = _heartbreaker(state, speaker_id)
    fact = _fact_about(speaker, subject_id)
    if fact is None:
        return None
    if fact.fact_key.endswith(".hidden_secret"):
        return None
    rng = SeededRng(f"{state.seed}:gossip:{state.day}:{state.turn_index}:{speaker_id}:{subject_id}")
    value = _distorted_value(state, fact, rng)
    known = KnownFact(
        fact_key=fact.fact_key,
        value=value,
        source="gossip",
        source_npc_id=speaker_id,
        learned_on_day=state.day,
        learned_on_turn=state.turn_index,
        confidence=0.6 if value == fact.value else 0.35,
        citation=f"{speaker.name} told you this on Day {state.day}.",
    )
    existing = state.player.known_facts.get(known.fact_key)
    if existing is None or existing.confidence < known.confidence:
        state.player.known_facts[known.fact_key] = known
    return known


def gossip_subjects_for(state: GameState, speaker_id: str) -> list[str]:
    """Return subject ids the speaker can gossip about.

    Only subjects that still resolve to a member of the current cast are
    offered. A fact whose subject id no longer maps to a live heartbreaker (e.g. a
    stale id carried in older save data, or a phantom left behind by a cast
    change) is dropped here so the follow-up menu never offers — and the turn
    loop never has to resolve — gossip about someone who is not in the resort.
    """
    speaker = _heartbreaker(state, speaker_id)
    cast_ids = {heartbreaker.id for heartbreaker in state.heartbreakers}
    subjects = {
        fact.fact_key.split(".", 1)[0]
        for fact in speaker.known_facts.values()
        if not fact.fact_key.endswith(".hidden_secret")
    }
    excluded = {"player", speaker_id}
    return sorted(
        subject for subject in subjects if subject in cast_ids and subject not in excluded
    )


def _fact_about(speaker: HeartbreakerState, subject_id: str) -> KnownFact | None:
    facts = [
        fact for fact in speaker.known_facts.values()
        if fact.fact_key.startswith(f"{subject_id}.") and not fact.fact_key.endswith(".hidden_secret")
    ]
    facts.sort(key=lambda fact: (fact.confidence, fact.fact_key), reverse=True)
    return facts[0] if facts else None


def _distorted_value(state: GameState, fact: KnownFact, rng: SeededRng) -> str:
    if rng.randint(1, 100) > 30:
        return fact.value
    subject_id, trait_key = fact.fact_key.split(".", 1)
    subject = next((heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == subject_id), None)
    if subject is None:
        # The fact's subject is no longer in the cast (stale id). Pass the value
        # through undistorted rather than hard-crashing the turn.
        return fact.value
    trait = subject.trait_card.core_traits.get(trait_key)
    if trait is None or not trait.distractors:
        return fact.value
    return rng.choice(trait.distractors)


def _heartbreaker(state: GameState, heartbreaker_id: str) -> HeartbreakerState:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == heartbreaker_id:
            return heartbreaker
    raise ValueError(f"unknown heartbreaker: {heartbreaker_id}")
