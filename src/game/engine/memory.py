"""Deterministic memory creation and storage helpers.

Design source:
- 07-Gossip-And-Information.md: The Gossip System

Memory text is flavor and excluded from state hashes. Memory identity and
metadata are deterministic so traces and replays remain stable.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Literal

from src.game.engine.ceremonies import CeremonyEvent
from src.game.state.memory import GossipSeed
from src.game.state.models import GameState, Memory, MemoryBatch


def create_memory(
    *,
    holder_id: str,
    subject_id: str,
    source: Literal["direct", "witnessed", "told_by"],
    day: int,
    turn: int,
    weight: int,
    tags: list[str],
    content: str,
    source_id: str | None = None,
    durable: bool = True,
) -> Memory:
    """Create one deterministic memory."""
    return Memory(
        id=_memory_id(holder_id, subject_id, source, day, turn, tags, source_id),
        holder_id=holder_id,
        subject_id=subject_id,
        content=content,
        source=source,
        source_id=source_id,
        formed_on_day=day,
        formed_on_turn=turn,
        emotional_weight=max(1, min(10, weight)),
        tags=sorted(set(tags)),
        durable=durable,
    )


def add_memory(state: GameState, memory: Memory) -> None:
    """Add a memory to the correct holder if it is not already present."""
    holder = _holder_memory_list(state, memory.holder_id)
    if any(existing.id == memory.id for existing in holder):
        return
    holder.append(memory)


def add_memory_batch(state: GameState, batch: MemoryBatch, *, day: int, turn: int) -> list[Memory]:
    """Create deterministic memories from one curator commit."""
    created: list[Memory] = []
    for draft in batch.memories:
        memory = create_memory(
            holder_id=draft.holder_id,
            subject_id=draft.subject_id,
            source=draft.source,
            source_id=draft.source_id,
            day=day,
            turn=turn,
            weight=draft.emotional_weight,
            tags=draft.tags,
            content=draft.content,
            durable=draft.durable,
        )
        add_memory(state, memory)
        created.append(memory)
    return created


def propagate_gossip_seeds(
    state: GameState,
    seeds: Sequence[GossipSeed],
    *,
    day: int,
    turn: int,
) -> list[Memory]:
    """Create deterministic secondhand memories from curator gossip seeds."""
    created: list[Memory] = []
    for seed in seeds:
        for listener_id in _interested_listeners(state, seed):
            if _has_similar_memory(state, listener_id, seed):
                continue
            memory = create_memory(
                holder_id=listener_id,
                subject_id=seed.subject_id,
                source="told_by",
                source_id=seed.holder_id,
                day=day,
                turn=turn,
                weight=max(2, seed.emotional_weight - 2),
                tags=[*seed.tags, "told_by", "gossip_spread"],
                content=seed.gist,
            )
            add_memory(state, memory)
            created.append(memory)
    return created


def remember_ceremony_events(state: GameState, events: Sequence[CeremonyEvent]) -> None:
    """Create witnessed memories for visible ceremony events."""
    for event in events:
        kind = event.kind
        message = event.message
        subject_id = event.islander_id or "villa"
        tags = [kind, "ceremony"]
        for holder_id in _all_holder_ids(state):
            add_memory(
                state,
                create_memory(
                    holder_id=holder_id,
                    subject_id=subject_id,
                    source="witnessed",
                    day=state.day,
                    turn=state.turn_index,
                    weight=7 if kind in {"bombshell", "elimination"} else 5,
                    tags=tags,
                    content=message,
                ),
            )


def _holder_memory_list(state: GameState, holder_id: str) -> list[Memory]:
    if holder_id == "player":
        return state.player.memories
    for islander in state.islanders:
        if islander.id == holder_id:
            return islander.memories
    raise ValueError(f"unknown memory holder: {holder_id}")


def _all_holder_ids(state: GameState) -> list[str]:
    return ["player"] + [islander.id for islander in state.islanders if not islander.eliminated]


def _interested_listeners(state: GameState, seed: GossipSeed) -> list[str]:
    valid_ids = set(_all_holder_ids(state))
    listeners = [
        listener_id
        for listener_id in seed.spreadable_to
        if listener_id in valid_ids and listener_id != seed.holder_id
    ]
    if listeners:
        return listeners[:3]
    return [
        islander.id
        for islander in state.islanders
        if not islander.eliminated and islander.id not in {seed.holder_id, seed.subject_id}
    ][:1]


def _has_similar_memory(state: GameState, listener_id: str, seed: GossipSeed) -> bool:
    holder = _holder_memory_list(state, listener_id)
    gist_tokens = set(seed.gist.lower().split())
    for memory in holder:
        if memory.subject_id != seed.subject_id:
            continue
        overlap = gist_tokens & set(memory.content.lower().split())
        if len(overlap) >= 4:
            return True
    return False


def _memory_id(
    holder_id: str,
    subject_id: str,
    source: str,
    day: int,
    turn: int,
    tags: list[str],
    source_id: str | None,
) -> str:
    raw = "|".join(
        [
            holder_id,
            subject_id,
            source,
            "" if source_id is None else source_id,
            str(day),
            str(turn),
            ",".join(sorted(tags)),
        ]
    )
    return "mem_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
