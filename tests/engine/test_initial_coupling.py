"""Tests for the day-one initial coupling ceremony."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction, available_actions
from src.game.engine.character_creation import create_character
from src.game.engine.turn import run_turn
from src.game.state.models import Couple, GameState, Gender, PlayerStats, new_game
from src.game.state.rng import SeededRng


def test_day1_initial_coupling_offered_to_player() -> None:
    state = _created_state(Gender.MAN)

    actions = available_actions(state)

    assert {spec.action.kind for spec in actions} == {ActionKind.RECOUPLE}
    assert len(actions) == 4
    assert {spec.action.target_id for spec in actions} == {
        "chloe",
        "maya",
        "sophie_start",
        "nia_start",
    }


def test_initial_coupling_pairs_player_without_eliminating_leftover_single() -> None:
    state = _created_state(Gender.MAN)

    result = run_turn(
        state,
        PlayerAction(kind=ActionKind.RECOUPLE, target_id="chloe"),
        SeededRng(1),
    )

    assert len(result.state.couples) == 4
    assert Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1) in result.state.couples
    assert not any(islander.eliminated for islander in result.state.islanders)


def _created_state(gender: Gender) -> GameState:
    state = new_game(1)
    create_character(
        state,
        archetype_id="heartthrob",
        gender=gender,
        stats=PlayerStats(charm=9, banter=6, eq=5, graft=5, loyalty=5),
    )
    return state
