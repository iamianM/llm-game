"""Tests for deterministic audience scoring."""

from __future__ import annotations

from src.game.engine.audience import audience_snapshot, couple_audience_score
from src.game.state.models import Couple, new_game


def test_audience_snapshot_includes_active_couples() -> None:
    """Audience ranking includes every active couple."""
    state = new_game(1)
    state.couples = [
        Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1),
        Couple(partner_a_id="maya", partner_b_id="liam", formed_on_day=1),
    ]

    snapshot = audience_snapshot(state)

    assert [entry.couple for entry in snapshot.entries] == [["maya", "liam"], ["player", "chloe"]]


def test_audience_snapshot_ranks_by_score_descending() -> None:
    """Higher public perception sorts first."""
    state = new_game(1)
    state.player.public_perception = 90
    state.couples = [
        Couple(partner_a_id="maya", partner_b_id="liam", formed_on_day=1),
        Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1),
    ]

    snapshot = audience_snapshot(state)

    assert snapshot.entries[0].couple == ["player", "chloe"]
    assert snapshot.entries[0].rank == 1


def test_audience_score_combines_perception_and_couple_strength() -> None:
    """The player's couple gets a small relationship-derived bonus."""
    state = new_game(1)
    state.player.public_perception = 50
    state.islanders[0].public_perception = 50
    state.islanders[0].relationship.affection = 40
    state.islanders[0].relationship.trust = 20
    couple = Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)

    assert couple_audience_score(state, couple) == 53


def test_audience_snapshot_excludes_eliminated_islanders() -> None:
    """Dumped islanders are no longer ranked in couples."""
    state = new_game(1)
    state.islanders[0].eliminated = True
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]

    snapshot = audience_snapshot(state)

    assert snapshot.entries == []


def test_audience_ranking_displays_1_of_4() -> None:
    """The H9 starting cast supports four ranked couples."""
    state = new_game(1)
    state.couples = [
        Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1),
        Couple(partner_a_id="maya", partner_b_id="liam", formed_on_day=1),
        Couple(partner_a_id="sophie", partner_b_id="marcus", formed_on_day=1),
        Couple(partner_a_id="nia", partner_b_id="blake", formed_on_day=1),
    ]

    snapshot = audience_snapshot(state)

    assert [entry.rank for entry in snapshot.entries] == [1, 2, 3, 4]
