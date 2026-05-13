"""Deterministic trace bookmarks for review packets."""

from __future__ import annotations

from src.game.engine.turn import TurnResult
from src.game.state.bookmarks import Bookmark


def bookmarks_for_turn(turn: TurnResult) -> list[Bookmark]:
    """Return structural bookmarks for one completed turn."""
    bookmarks: list[Bookmark] = []
    turn_index = turn.state.turn_index
    for event in turn.ceremony_events:
        bookmarks.append(
            Bookmark(
                turn=turn_index,
                kind=event.kind,
                category="event",
                title=event.kind.replace("_", " ").title(),
                note=event.message,
            )
        )
    pull = turn.mechanical_result.pull_attempt
    if pull is not None and not pull.success:
        bookmarks.append(
            Bookmark(
                turn=turn_index,
                kind="pull_failed",
                category="anomaly",
                title="Pull failed",
                note=f"{pull.target_id} declined the pull.",
            )
        )
    active = turn.state.active_conversation
    if active is not None and active.pending_interruption is not None:
        bookmarks.append(
            Bookmark(
                turn=turn_index,
                kind="interruption",
                category="highlight",
                title="NPC interruption",
                note=f"{active.pending_interruption.interrupter_id} interrupted the conversation.",
            )
        )
    for batch in turn.curator_batches:
        for memory in batch.memories:
            if memory.emotional_weight >= 8:
                bookmarks.append(
                    Bookmark(
                        turn=turn_index,
                        kind="high_weight_memory",
                        category="highlight",
                        title="High-weight memory",
                        note=f"{memory.holder_id} remembers {memory.subject_id}: {memory.content}",
                    )
                )
    if turn.auto_advance:
        bookmarks.append(
            Bookmark(
                turn=turn_index,
                kind="auto_advance",
                category="event",
                title="Time expired",
                note="The phase advanced automatically.",
            )
        )
    return bookmarks
