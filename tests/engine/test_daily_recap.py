"""Tests for daily recap creation."""

from __future__ import annotations

from src.game.engine.daily_recap import append_daily_recap_if_needed
from src.game.engine.memory import add_memory, create_memory
from src.game.state.models import new_game


def test_daily_recap_appends_once_per_completed_day() -> None:
    state = new_game(1)
    memory = create_memory(
        holder_id="chloe",
        subject_id="player",
        source="direct",
        day=1,
        turn=3,
        weight=8,
        tags=["spark"],
        content="Chloe remembered a villa-defining moment.",
    )
    add_memory(state, memory)
    state.day = 2

    first = append_daily_recap_if_needed(state, 1)
    second = append_daily_recap_if_needed(state, 1)

    assert first is not None
    assert second is None
    assert [recap.day for recap in state.daily_recaps] == [1]
    assert state.daily_recaps[0].items[0].content == memory.content


def test_daily_recap_waits_until_day_rolls_forward() -> None:
    state = new_game(1)

    recap = append_daily_recap_if_needed(state, 1)

    assert recap is None
    assert state.daily_recaps == []


def test_daily_recap_rewrites_the_player_label_to_second_person() -> None:
    state = new_game(1)
    memory = create_memory(
        holder_id="chloe",
        subject_id="player",
        source="direct",
        day=1,
        turn=3,
        weight=8,
        tags=["warmth"],
        content="I appreciated the player checking in, and the player's calm steadied me.",
    )
    add_memory(state, memory)
    state.day = 2

    recap = append_daily_recap_if_needed(state, 1)

    assert recap is not None
    surfaced = recap.items[0].content
    assert "the player" not in surfaced
    assert surfaced == "I appreciated you checking in, and your calm steadied me."
    # The underlying memory keeps its name-agnostic phrasing.
    assert "the player" in state.islanders[0].memories[-1].content


def test_daily_recap_capitalizes_sentence_initial_player_label() -> None:
    state = new_game(1)
    memory = create_memory(
        holder_id="chloe",
        subject_id="player",
        source="direct",
        day=1,
        turn=4,
        weight=7,
        tags=["honesty"],
        content="The player's honesty surprised me. The player owned it.",
    )
    add_memory(state, memory)
    state.day = 2

    recap = append_daily_recap_if_needed(state, 1)

    assert recap is not None
    assert recap.items[0].content == "Your honesty surprised me. You owned it."
