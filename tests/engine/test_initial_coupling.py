"""Tests for the day-one initial coupling ceremony."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction, available_actions
from src.game.engine.character_creation import create_character
from src.game.engine.turn import run_turn
from src.game.state.models import Couple, GameState, Gender, Phase, PlayerStats, new_game
from src.game.state.phase_clock import PhaseClock
from src.game.state.rng import SeededRng


def test_day1_initial_coupling_offered_to_player() -> None:
    state = _created_state(Gender.MAN)

    actions = available_actions(state)

    assert {spec.action.kind for spec in actions} == {ActionKind.PAIR}
    assert len(actions) == 4
    assert {spec.action.target_id for spec in actions} == {
        "chloe",
        "maya",
        "sophie",
        "nia",
    }


def test_initial_coupling_pairs_player_without_eliminating_leftover_single() -> None:
    state = _created_state(Gender.MAN)

    result = run_turn(
        state,
        PlayerAction(kind=ActionKind.PAIR, target_id="chloe"),
        SeededRng(1),
    )

    assert len(result.state.couples) == 4
    assert (
        Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1, formed_via="opening")
        in result.state.couples
    )
    assert result.state.heartbreakers[0].familiarity_with_player == 25
    assert not any(heartbreaker.eliminated for heartbreaker in result.state.heartbreakers)


def _created_state(gender: Gender) -> GameState:
    state = new_game(1)
    create_character(
        state,
        archetype_id="heartthrob",
        gender=gender,
        stats=PlayerStats(charm=9, banter=6, eq=5, spark=5, loyalty=5),
    )
    # Day-1 now starts in INTROS for the greeting circle. Skip past them for
    # tests that focus on the First Spark / coupling flow.
    state.phase = Phase.MORNING
    state.phase_clock = PhaseClock(phase=Phase.MORNING.value, budget_minutes=120)
    state.intro_completed_ids = [
        heartbreaker.id for heartbreaker in state.heartbreakers if not heartbreaker.eliminated
    ]
    state.intro_memory_created = True
    return state
