"""Daily background recap generation."""

from __future__ import annotations

import re

from src.game.state.models import DailyRecap, DailyRecapItem, GameState, Memory

_PLAYER_POSSESSIVE_RE = re.compile(r"\bthe player's\b", re.IGNORECASE)
_PLAYER_RE = re.compile(r"\bthe player\b", re.IGNORECASE)


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
                content=humanize_player_reference(memory.content),
                emotional_weight=memory.emotional_weight,
                tags=list(memory.tags),
            )
            for memory in _notable_memories(state, completed_day)
        ],
    )
    state.daily_recaps.append(recap)
    return recap


def humanize_player_reference(content: str) -> str:
    """Rewrite the curator's name-agnostic "the player" into second person.

    Islander memories are stored in a name-agnostic voice ("the player") so they
    stay reusable across surfaces, but the daily recap is read *by* the player.
    Surfacing the raw label ("I appreciated the player checking in") breaks
    immersion, so the player-facing recap addresses them directly ("I
    appreciated you checking in"). The underlying memory is left untouched.
    """

    def _possessive(match: re.Match[str]) -> str:
        return "Your" if match.group(0)[0].isupper() else "your"

    def _plain(match: re.Match[str]) -> str:
        return "You" if match.group(0)[0].isupper() else "you"

    content = _PLAYER_POSSESSIVE_RE.sub(_possessive, content)
    return _PLAYER_RE.sub(_plain, content)


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
