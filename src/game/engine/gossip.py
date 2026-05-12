"""Memory-backed gossip mechanics."""

from __future__ import annotations

from src.game.engine.memory import add_memory, create_memory
from src.game.state.models import GameState, RelationshipDelta


def apply_gossip_follow_up(
    state: GameState,
    source_id: str,
    intent_kind: str,
    success: bool,
) -> RelationshipDelta:
    """Apply a gossip follow-up and transfer the memory on success."""
    memory_id = intent_kind.removeprefix("ask_gossip:")
    conversation = state.active_conversation
    if conversation is None:
        raise ValueError("gossip follow-up requires active conversation")
    source_memory = next(
        (memory for memory in conversation.gossip_offers if memory.id == memory_id),
        None,
    )
    if source_memory is None:
        raise ValueError(f"gossip memory not offered: {memory_id}")
    if not success:
        return RelationshipDelta()
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
        ),
    )
    return RelationshipDelta(trust=2)
