"""Daily background recap generation."""

from __future__ import annotations

from src.game.state.models import DailyRecap, DailyRecapItem, GameState, Memory


def append_daily_recap_if_needed(state: GameState, completed_day: int) -> DailyRecap | None:
    """Append one recap for ``completed_day`` if the clock has rolled forward."""
    if state.day <= completed_day or any(recap.day == completed_day for recap in state.daily_recaps):
        return None
    recap = DailyRecap(
        day=completed_day,
        items=[
            DailyRecapItem(
                holder_id=memory.holder_id,
                subject_id=memory.subject_id,
                content=memory.content,
                emotional_weight=memory.emotional_weight,
                tags=list(memory.tags),
            )
            for memory in _notable_memories(state, completed_day)
        ],
    )
    state.daily_recaps.append(recap)
    return recap


def _notable_memories(state: GameState, day: int) -> list[Memory]:
    memories = [
        memory
        for islander in state.islanders
        for memory in islander.memories
        if memory.formed_on_day == day
    ]
    memories.extend(memory for memory in state.player.memories if memory.formed_on_day == day)
    memories.sort(key=lambda memory: (-memory.emotional_weight, memory.formed_on_turn, memory.id))
    seen: set[tuple[str, str, str]] = set()
    unique: list[Memory] = []
    for memory in memories:
        key = (memory.holder_id, memory.subject_id, memory.content)
        if key in seen:
            continue
        seen.add(key)
        unique.append(memory)
        if len(unique) == 5:
            break
    return unique
