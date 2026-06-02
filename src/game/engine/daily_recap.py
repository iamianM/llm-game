"""Daily background recap generation."""

from __future__ import annotations

import re

from src.game.state.models import DailyRecap, DailyRecapItem, GameState, Memory

# Accept an optional "the " so a bare subject label ("Player guessed wrong ...")
# is rewritten alongside the name-agnostic "the player" voice. Capitalization of
# the replacement follows the first matched character ("The"/"Player" -> "You").
_PLAYER_POSSESSIVE_RE = re.compile(r"\b(?:the )?player's\b", re.IGNORECASE)
_PLAYER_RE = re.compile(r"\b(?:the )?player\b", re.IGNORECASE)

# "While you were busy" surfaces background *whispers* — relationship beats and
# gossip that drifted back to the player. Two families of memory are NOT
# whispers and must be kept out of the player-facing digest:
#
#   * Procedural resort announcements the whole cast witnessed together (flame_deck
#     gathers, pairing/Pairing ceremonies, eliminations, challenges, Flush of
#     Hearts/Flush announcements, producer text). Several carry internal labels
#     ("Pairing Ceremony text: ..."), raw cast ids ("jordan_start leaves"), or
#     mechanical scoring ("ended in failure (3 pts)") that read like leaked
#     stage directions. ``remember_ceremony_events`` stamps *every* one of these
#     with the ``"ceremony"`` tag, so matching that single tag drops them all —
#     including any future event kind — without an event-by-event denylist.
#   * Internal, tag-only mechanical markers the producer / Conversation Curator
#     reference later but that were never written for display (e.g.
#     ``caught_unprepared`` quiz reactions phrased in a bare first person —
#     "...about my age..." — that read as orphaned without holder attribution).
#
# Dropping both lets the curator's genuine personal beats (or the honest "no
# whispers" fallback) carry the recap instead.
_NON_WHISPER_TAGS = frozenset({"ceremony", "caught_unprepared"})


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
        if memory.formed_on_day == day and not _is_non_whisper(memory)
    ]
    memories.extend(
        memory
        for memory in state.player.memories
        if memory.formed_on_day == day and not _is_non_whisper(memory)
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
    return _diversify(unique)


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


def _diversify(memories: list[Memory], slots: int = 5) -> list[Memory]:
    """Pick up to ``slots`` memories, favouring storyline variety over depth.

    Pass one takes the strongest memory from each distinct storyline (already in
    weight order), so the reader hears from several corners of the resort. If
    slots remain, pass two backfills the next-strongest leftovers — so a quiet
    day with only one storyline still fills the digest rather than going sparse.
    """
    chosen: list[Memory] = []
    leftovers: list[Memory] = []
    seen_pairs: set[frozenset[str]] = set()
    for memory in memories:
        key = _pair_key(memory)
        if key in seen_pairs:
            leftovers.append(memory)
            continue
        seen_pairs.add(key)
        chosen.append(memory)
        if len(chosen) == slots:
            return chosen
    for memory in leftovers:
        if len(chosen) == slots:
            break
        chosen.append(memory)
    return chosen


def _is_non_whisper(memory: Memory) -> bool:
    """True for procedural announcements / internal markers that aren't whispers."""
    return bool(_NON_WHISPER_TAGS.intersection(memory.tags))
