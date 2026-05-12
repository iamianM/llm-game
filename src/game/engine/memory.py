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
from src.game.state.models import Conversation, GameState, Memory


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
    )


def add_memory(state: GameState, memory: Memory) -> None:
    """Add a memory to the correct holder if it is not already present."""
    holder = _holder_memory_list(state, memory.holder_id)
    if any(existing.id == memory.id for existing in holder):
        return
    holder.append(memory)


def remember_conversation_close(state: GameState, conversation: Conversation) -> None:
    """Create direct memories for the player and target when a conversation closes."""
    if not conversation.exchanges:
        return
    target = _islander_name(state, conversation.target_id)
    tags = list(conversation.accumulated_tags)
    weight = _conversation_weight(conversation)
    location = state.location_id.value
    player_content = (
        f"I had a {', '.join(tags[:3]) or 'private'} conversation with {target} "
        f"at the {location} on day {state.day}."
    )
    target_content = (
        f"The player had a {', '.join(tags[:3]) or 'private'} conversation with me "
        f"at the {location} on day {state.day}."
    )
    add_memory(
        state,
        create_memory(
            holder_id="player",
            subject_id=conversation.target_id,
            source="direct",
            day=state.day,
            turn=state.turn_index,
            weight=weight,
            tags=tags,
            content=player_content,
        ),
    )
    add_memory(
        state,
        create_memory(
            holder_id=conversation.target_id,
            subject_id="player",
            source="direct",
            day=state.day,
            turn=state.turn_index,
            weight=weight,
            tags=tags,
            content=target_content,
        ),
    )


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


def _conversation_weight(conversation: Conversation) -> int:
    affection = sum(
        delta.affection
        for record in conversation.exchanges
        for delta in record.relationship_deltas.values()
    )
    return max(1, min(10, (affection // 2) + 3))


def _islander_name(state: GameState, islander_id: str) -> str:
    for islander in state.islanders:
        if islander.id == islander_id:
            return islander.name
    return islander_id


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
