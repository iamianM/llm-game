"""Tests for deterministic gossip-seed propagation."""

from __future__ import annotations

from src.game.engine.memory import add_memory, create_memory, propagate_gossip_seeds
from src.game.state.memory import GossipSeed
from src.game.state.models import new_game


def test_propagate_gossip_seeds_creates_told_by_memory_on_listener() -> None:
    state = new_game(1)
    seed = GossipSeed(
        subject_id="chloe",
        gist="Chloe looked rattled after Jordan stepped back at the flame_deck.",
        holder_id="maya",
        spreadable_to=["liam"],
        emotional_weight=8,
        tags=["gossip"],
    )

    memories = propagate_gossip_seeds(state, [seed], day=2, turn=7)

    assert len(memories) == 1
    assert memories[0].holder_id == "liam"
    assert memories[0].source == "told_by"
    assert memories[0].source_id == "maya"


def test_propagation_attenuates_weight() -> None:
    state = new_game(1)
    seed = GossipSeed(
        subject_id="chloe",
        gist="Chloe seemed unsure about the pairing.",
        holder_id="maya",
        spreadable_to=["liam"],
        emotional_weight=7,
        tags=["gossip"],
    )

    memories = propagate_gossip_seeds(state, [seed], day=2, turn=7)

    assert memories[0].emotional_weight == 5


def test_propagation_skips_unknown_listener() -> None:
    state = new_game(1)
    seed = GossipSeed(
        subject_id="chloe",
        gist="Chloe seemed unsure about the pairing.",
        holder_id="maya",
        spreadable_to=["unknown"],
        emotional_weight=7,
        tags=["gossip"],
    )

    memories = propagate_gossip_seeds(state, [seed], day=2, turn=7)

    assert memories
    assert memories[0].holder_id != "unknown"


def test_propagation_dedupes_against_existing_memories() -> None:
    state = new_game(1)
    add_memory(
        state,
        create_memory(
            holder_id="liam",
            subject_id="chloe",
            source="told_by",
            source_id="maya",
            day=2,
            turn=6,
            weight=5,
            tags=["gossip"],
            content="Chloe looked rattled after Jordan stepped back at the flame_deck.",
        ),
    )
    seed = GossipSeed(
        subject_id="chloe",
        gist="Chloe looked rattled after Jordan stepped back at the flame_deck.",
        holder_id="maya",
        spreadable_to=["liam"],
        emotional_weight=8,
        tags=["gossip"],
    )

    memories = propagate_gossip_seeds(state, [seed], day=2, turn=7)

    assert memories == []
