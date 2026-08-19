"""Deterministic memory creation and storage helpers.

Design source:
- docs/design/07-Gossip-And-Information.md: The Gossip System

Memory text is flavor and excluded from state hashes. Memory identity and
metadata are deterministic so traces and replays remain stable.
"""

from __future__ import annotations

import hashlib
import re
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
    """Add a memory to the correct holder if it is not already present.

    Derives ``mentioned_subject_ids`` here — the single storage choke point that
    has the live cast roster — so every stored memory carries the typed list the
    voice context reads instead of regex-scanning content at exchange time
    (ENGINEERING R18: derive at the boundary, store typed, read structurally).
    """
    holder = _holder_memory_list(state, memory.holder_id)
    if any(existing.id == memory.id for existing in holder):
        return
    if not memory.mentioned_subject_ids:
        memory.mentioned_subject_ids = _mentioned_subject_ids(state, memory.content)
    holder.append(memory)


def _mentioned_subject_ids(state: GameState, content: str) -> list[str]:
    """Cast ids whose display name appears (word-boundary) in ``content``.

    Deterministic over the live cast in roster order. This is the boundary-side
    home of the word-boundary match the exchange validator uses, so the two stay
    in lockstep without the voice context re-scanning prose at read time.
    """
    if not content:
        return []
    mentioned: list[str] = []
    for heartbreaker in state.heartbreakers:
        if re.search(rf"\b{re.escape(heartbreaker.name)}\b", content):
            mentioned.append(heartbreaker.id)
    return mentioned


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
                # "gossip" is the positive flag the follow-up menu's
                # shareable-gossip allowlist keys on; propagated seeds are
                # gossip by definition, so tag them explicitly rather than
                # relying on the curator to have set it on every seed.
                tags=[*seed.tags, "told_by", "gossip_spread", "gossip"],
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
        subject_id = event.heartbreaker_id or "resort"
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
                    weight=7 if kind in {"heart_throb", "elimination"} else 5,
                    tags=tags,
                    content=message,
                ),
            )


def _holder_memory_list(state: GameState, holder_id: str) -> list[Memory]:
    if holder_id == "player":
        return state.player.memories
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == holder_id:
            return heartbreaker.memories
    raise ValueError(f"unknown memory holder: {holder_id}")


def _all_holder_ids(state: GameState) -> list[str]:
    return ["player"] + [heartbreaker.id for heartbreaker in state.heartbreakers if not heartbreaker.eliminated]


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
        heartbreaker.id
        for heartbreaker in state.heartbreakers
        if not heartbreaker.eliminated and heartbreaker.id not in {seed.holder_id, seed.subject_id}
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
