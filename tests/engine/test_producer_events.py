"""Tests for deterministic producer text scheduling."""

from __future__ import annotations

from src.game.engine.producer_events import schedule_producer_text
from src.game.state.models import Mood, new_game


def test_welcome_text_fires_day_one() -> None:
    state = new_game(1)

    text = schedule_producer_text(1, state)

    assert text is not None
    assert text.kind == "welcome"


def test_group_date_invite_creates_pending_group_date() -> None:
    state = new_game(1)

    text = schedule_producer_text(2, state)

    assert text is not None
    assert state.pending_group_date is not None
    assert state.pending_group_date.participants == ["player", "chloe", "maya"]


def test_coupling_warning_text_sets_anxious_moods() -> None:
    state = new_game(1)

    text = schedule_producer_text(3, state)

    assert text is not None
    assert all(islander.mood is Mood.ANXIOUS for islander in state.islanders)


def test_bombshell_arrival_tease_precedes_aisha() -> None:
    state = new_game(1)

    text = schedule_producer_text(4, state)

    assert text is not None
    assert text.kind == "bombshell_arrival_tease"


def test_final_vote_announce_text_day_six() -> None:
    state = new_game(1)

    text = schedule_producer_text(6, state)

    assert text is not None
    assert text.kind == "final_vote_announce"


def test_producer_text_does_not_fire_off_schedule() -> None:
    state = new_game(1)

    assert schedule_producer_text(5, state) is None
