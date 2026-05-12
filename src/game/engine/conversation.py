"""Deterministic conversation lifecycle helpers.

Design sources:
- 11-Conversation-Flow.md: Organic Conversation Endings
- 05-Interaction-System.md: Conversation Structure & Continuity
"""

from __future__ import annotations

from typing import Literal, Protocol

from src.game.engine.rules import MechanicalResult
from src.game.state.models import (
    Conversation,
    ExchangeRecord,
    GameState,
    IslanderState,
    Memory,
    Mood,
)

MAX_RETAINED_EXCHANGES = 8


class ExchangeLike(Protocol):
    """The dialogue fields needed to persist an exchange record."""

    @property
    def player_dialogue(self) -> str: ...

    @property
    def npc_dialogue(self) -> str: ...

    @property
    def npc_tone(self) -> str: ...

    @property
    def npc_mood_after(self) -> Mood: ...


def start_conversation(state: GameState, target_id: str, turn_index: int) -> Conversation:
    """Open a new active conversation."""
    if state.active_conversation is not None:
        raise ValueError("cannot start a conversation while another is active")
    conversation = Conversation(
        target_id=target_id,
        started_on_turn=turn_index,
        started_on_day=state.day,
        gossip_offers=eligible_gossip_memories(state, target_id),
    )
    state.active_conversation = conversation
    return conversation


def eligible_gossip_memories(state: GameState, target_id: str) -> list[Memory]:
    """Return gossip memories the target may share with the player."""
    target = _target_islander(state, target_id)
    if target.relationship.affection < 25:
        return []
    known_source_ids = {
        tag.removeprefix("source_memory:")
        for memory in state.player.memories
        for tag in memory.tags
        if tag.startswith("source_memory:")
    }
    return [
        memory
        for memory in target.memories
        if memory.subject_id != "player"
        and memory.emotional_weight >= 4
        and memory.id not in known_source_ids
    ][:3]


def append_exchange(
    conversation: Conversation,
    result: MechanicalResult,
    exchange: ExchangeLike,
    *,
    turn_index: int,
) -> ExchangeRecord:
    """Append one exchange and retain the recent history cap."""
    intent_id = result.action.intent_id
    if intent_id is None:
        raise ValueError("exchange result is missing intent_id")
    record = ExchangeRecord(
        turn_index=turn_index,
        intent_id=intent_id,
        player_dialogue=exchange.player_dialogue,
        npc_dialogue=exchange.npc_dialogue,
        npc_tone=exchange.npc_tone,
        npc_mood_after=exchange.npc_mood_after,
        success=result.success,
        tags=result.tags,
        relationship_deltas=result.relationship_deltas,
    )
    conversation.exchanges.append(record)
    conversation.exchanges = conversation.exchanges[-MAX_RETAINED_EXCHANGES:]
    conversation.accumulated_tags.extend(result.tags)
    return record


def close_conversation(
    state: GameState,
    reason: Literal["player_exit", "npc_left", "phase_end"],
) -> None:
    """Close the active conversation and remove it from canonical state."""
    if state.active_conversation is None:
        raise ValueError("no active conversation to close")
    state.active_conversation.status = "closed"
    state.active_conversation = None


def departure_probability(conversation: Conversation, state: GameState) -> int:
    """Return deterministic 0-90 NPC departure probability."""
    chance = 0
    exchange_count = len(conversation.exchanges)
    if exchange_count > 10:
        chance += 30
    if exchange_count > 15:
        chance += 30

    recent = conversation.exchanges[-5:]
    recent_affection = sum(
        sum(delta.affection for delta in record.relationship_deltas.values())
        for record in recent
    )
    if recent_affection < 0:
        chance += 40
    if recent_affection > 20:
        chance -= 30

    if any("vulnerable" in record.tags or "deep" in record.tags for record in recent):
        chance -= 20
    if recent and not recent[-1].success:
        chance += 25
    if _last_two_repeat(conversation):
        chance += 20

    target = _target_relationship_strength(state, conversation.target_id)
    if target < 40:
        chance += 10
    if target > 120:
        chance -= 20

    return max(0, min(90, chance))


def _last_two_repeat(conversation: Conversation) -> bool:
    if len(conversation.exchanges) < 2:
        return False
    return conversation.exchanges[-1].intent_id == conversation.exchanges[-2].intent_id


def _target_relationship_strength(state: GameState, target_id: str) -> int:
    rel = _target_islander(state, target_id).relationship
    return rel.affection + rel.chemistry + rel.trust + rel.friendship


def _target_islander(state: GameState, target_id: str) -> IslanderState:
    for islander in state.islanders:
        if islander.id == target_id:
            return islander
    raise ValueError(f"unknown conversation target: {target_id}")
