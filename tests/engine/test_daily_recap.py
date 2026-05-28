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
