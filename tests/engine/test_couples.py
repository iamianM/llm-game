"""Tests for H4 couple strength and steal math."""

from __future__ import annotations

from src.game.engine.couples import (
    couple_strength,
    ranked_couples,
    resolve_steal_attempt,
    steal_chance,
)
from src.game.state.models import Couple, new_game
from src.game.state.rng import SeededRng


def test_couple_strength_averages_partners_relationships() -> None:
    state = new_game(1)
    chloe = state.islanders[0]
    chloe.relationship.affection = 80
    chloe.relationship.trust = 60
    couple = Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)

    assert couple_strength(state, couple) == 70


def test_couple_strength_zero_when_no_relationship() -> None:
    state = new_game(1)
    couple = Couple(partner_a_id="maya", partner_b_id="liam", formed_on_day=1)

    assert couple_strength(state, couple) == 3


def test_couple_ranking_orders_by_strength_then_perception() -> None:
    state = new_game(1)
    state.islanders[0].relationship.affection = 90
    state.islanders[0].relationship.trust = 70
    state.couples = [
        Couple(partner_a_id="maya", partner_b_id="liam", formed_on_day=1),
        Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1),
    ]

    assert ranked_couples(state)[0][0].partner_b_id == "chloe"


def test_steal_chance_includes_chemistry_minus_couple_strength() -> None:
    state = new_game(1)
    bombshell = state.islanders[1]
    bombshell.archetype = "bombshell"
    bombshell.relationship.chemistry = 5
    couple = Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)

    assert steal_chance(state, bombshell, "chloe", couple) == 70


def test_steal_chance_clamped_to_10_90() -> None:
    state = new_game(1)
    bombshell = state.islanders[1]
    couple = Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)
    bombshell.relationship.chemistry = 100

    assert steal_chance(state, bombshell, "chloe", couple) == 90


def test_steal_success_swaps_partners() -> None:
    state = new_game(1)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]
    bombshell = state.islanders[1]
    bombshell.relationship.chemistry = 100

    attempt = resolve_steal_attempt(state, bombshell.id, state.couples[0], SeededRng(1))

    assert attempt.success is True
    assert state.couples[0].partner_a_id == bombshell.id


def test_steal_failure_keeps_couple_intact() -> None:
    state = new_game(1)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]
    state.islanders[0].relationship.affection = 90
    state.islanders[0].relationship.trust = 90
    bombshell = state.islanders[1]
    bombshell.relationship.chemistry = 0

    attempt = resolve_steal_attempt(state, bombshell.id, state.couples[0], SeededRng(1))

    assert attempt.success is False
    assert state.couples[0].partner_a_id == "player"
