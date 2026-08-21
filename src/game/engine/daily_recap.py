"""Daily background recap generation."""

from __future__ import annotations

import re

from src.game.state.memory import RecapDisposition
from src.game.state.models import DailyRecap, DailyRecapItem, GameState, Memory

# Accept an optional "the " so a bare subject label ("Player guessed wrong ...")
# is rewritten alongside the name-agnostic "the player" voice. Capitalization of
# the replacement follows the first matched character ("The"/"Player" -> "You").
_PLAYER_POSSESSIVE_RE = re.compile(r"\b(?:the )?player's\b", re.IGNORECASE)
_PLAYER_RE = re.compile(r"\b(?:the )?player\b", re.IGNORECASE)

def append_daily_recap_if_needed(state: GameState, completed_day: int) -> DailyRecap | None:
    """Append one recap for ``completed_day`` if the clock has rolled forward."""
    if state.day <= completed_day or any(recap.day == completed_day for recap in state.daily_recaps):
        return None
    recap = DailyRecap(
        day=completed_day,
        resort_id=state.resort,
        items=[
            DailyRecapItem(
                holder_id=memory.holder_id,
                subject_id=memory.subject_id,
                content=memory.content,
                formed_on_turn=memory.formed_on_turn,
                emotional_weight=memory.emotional_weight,
                tags=list(memory.tags),
                recap_disposition=memory.recap_disposition,
            )
            for memory in _notable_memories(state, completed_day)
        ],
    )
    state.daily_recaps.append(recap)
    return recap


def humanize_player_reference(content: str) -> str:
    """Rewrite the curator's name-agnostic "the player" into second person.

    Heartbreaker memories are stored in a name-agnostic voice ("the player") so they
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
        for heartbreaker in state.heartbreakers
        for memory in heartbreaker.memories
        if memory.formed_on_day == day
        and memory.recap_disposition is not RecapDisposition.NONE
    ]
    memories.extend(
        memory
        for memory in state.player.memories
        if memory.formed_on_day == day
        and memory.recap_disposition is not RecapDisposition.NONE
    )
    memories.sort(key=lambda memory: (-memory.emotional_weight, memory.formed_on_turn, memory.id))
    # Witnessed ceremony events (challenges, pairings) are stored once per
    # holder with identical content, so a holder-scoped key would let the same
    # line fill all five slots ("The Couples Quiz tested Banter ..." x5). Dedupe
    # on the normalized text itself: identical wording carries identical news to
    # the reader, while per-heartbreaker personalized memories stay distinct.
    seen_content: set[str] = set()
    unique: list[Memory] = []
    for memory in memories:
        content_key = " ".join(memory.content.lower().split())
        if content_key in seen_content:
            continue
        seen_content.add(content_key)
        unique.append(memory)
    return _select_sections(unique)


def _pair_key(memory: Memory) -> frozenset[str]:
    """The two-person storyline a memory belongs to (order-independent).

    A budding Heart-Throb romance can spawn four or five distinct memories in a
    single day — both principals' versions plus the couple announcement — and
    they'd otherwise sweep every recap slot, burying the player's own beats and
    the rest of the resort under one pair's saga. Grouping by the unordered
    {holder, subject} pair lets the recap survey several storylines first.
    """
    subject = memory.subject_id or memory.holder_id
    return frozenset({memory.holder_id, subject})


def _select_sections(memories: list[Memory], slots: int = 5) -> list[Memory]:
    """Reserve both visible sections, then favour distinct strong storylines."""
    chosen: list[Memory] = []
    for disposition in (
        RecapDisposition.YOUR_DAY,
        RecapDisposition.WHILE_BUSY,
    ):
        strongest = next(
            (memory for memory in memories if memory.recap_disposition is disposition),
            None,
        )
        if strongest is not None:
            chosen.append(strongest)

    remaining = [memory for memory in memories if memory not in chosen]
    seen_pairs = {_pair_key(memory) for memory in chosen}
    repeated_storylines: list[Memory] = []
    for memory in remaining:
        if len(chosen) == slots:
            break
        pair = _pair_key(memory)
        if pair in seen_pairs:
            repeated_storylines.append(memory)
            continue
        seen_pairs.add(pair)
        chosen.append(memory)

    for memory in repeated_storylines:
        if len(chosen) == slots:
            break
        chosen.append(memory)

    section_order = {
        RecapDisposition.YOUR_DAY: 0,
        RecapDisposition.WHILE_BUSY: 1,
    }
    return sorted(
        chosen,
        key=lambda memory: (
            section_order[memory.recap_disposition],
            memory.formed_on_turn,
            memory.id,
        ),
    )
