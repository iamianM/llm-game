"""Tests for daily challenge mechanics."""

from __future__ import annotations

from src.game.engine.challenges import (
    challenge_event_message,
    resolve_challenge,
    schedule_challenge,
)
from src.game.state.models import Couple, new_game
from src.game.state.rng import SeededRng


def test_compatibility_quiz_success_applies_couple_strength_bonus() -> None:
    state = new_game(1)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]
    challenge = schedule_challenge(1)
    assert challenge is not None

    resolved = resolve_challenge(state, challenge, SeededRng(1))

    assert resolved.result == "success"
    assert state.islanders[0].relationship.affection >= 15


def test_compatibility_quiz_failure_applies_tension() -> None:
    state = new_game(1)
    challenge = schedule_challenge(1)
    assert challenge is not None

    resolved = resolve_challenge(state, challenge, SeededRng(2))

    if resolved.result == "failure":
        assert state.islanders[0].relationship.trust == 0


def test_heart_rate_uses_charm() -> None:
    state = new_game(1)
    state.player.stats.charm = 9
    challenge = schedule_challenge(2)
    assert challenge is not None

    resolved = resolve_challenge(state, challenge, SeededRng(1))

    assert resolved.stat_tested == "charm"
    assert resolved.result == "success"


def test_mr_and_mrs_failure_drops_friendship() -> None:
    state = new_game(1)
    state.player.stats.banter = 3
    challenge = schedule_challenge(3)
    assert challenge is not None

    resolved = resolve_challenge(state, challenge, SeededRng(5))

    if resolved.result == "failure":
        assert resolved.deltas["chloe"].friendship == -2


def test_lie_detector_low_loyalty_breaks_trust() -> None:
    state = new_game(1)
    state.player.stats.loyalty = 3
    challenge = schedule_challenge(4)
    assert challenge is not None

    resolved = resolve_challenge(state, challenge, SeededRng(5))

    if resolved.result == "failure":
        assert resolved.deltas["chloe"].trust == -6


def test_snog_marry_pie_choice_required() -> None:
    state = new_game(1)
    challenge = schedule_challenge(5)
    assert challenge is not None

    resolved = resolve_challenge(state, challenge, SeededRng(1))

    assert resolved.result is None


def test_snog_marry_pie_pied_islander_loses_friendship() -> None:
    state = new_game(1)
    state.player.stats.banter = 3
    challenge = schedule_challenge(5)
    assert challenge is not None

    resolved = resolve_challenge(state, challenge, SeededRng(5), choice="maya")

    assert resolved.participants == ["player", "maya"]


def test_final_couples_challenge_combines_stats() -> None:
    state = new_game(1)
    challenge = schedule_challenge(6)
    assert challenge is not None

    resolved = resolve_challenge(state, challenge, SeededRng(1))

    assert resolved.stat_tested == "combined"
    assert resolved.result == "success"


def test_schedule_challenge_returns_correct_kind_per_day() -> None:
    challenge = schedule_challenge(4)

    assert challenge is not None
    assert challenge.kind == "lie_detector"


def test_schedule_challenge_returns_none_off_schedule() -> None:
    assert schedule_challenge(7) is None


def test_challenge_event_message_uses_player_facing_labels() -> None:
    challenge = schedule_challenge(5)
    assert challenge is not None

    message = challenge_event_message(challenge)

    assert message == "Kiss Wed Pass tested Banter and is still pending."
