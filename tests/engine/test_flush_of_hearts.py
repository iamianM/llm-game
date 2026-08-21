"""Tests for the Flush of Hearts flow."""

from __future__ import annotations

import pytest

from src.game.agents.resort_orchestrator import NPCMovement, ResortUpdate, _render_context
from src.game.agents.turn_agents import mock_turn_agents
from src.game.engine.actions import ActionKind, PlayerAction, available_actions
from src.game.engine.flush_of_hearts import (
    apply_flush_decision,
    compute_npc_flush_choices,
    enter_flush_of_hearts,
    locations_for_resort,
    return_ceremony,
)
from src.game.engine.resort import validate_resort_update
from src.game.engine.turn import run_turn
from src.game.state.flush import FlushDecision, ResortName
from src.game.state.models import Couple, Location, Phase, new_game
from src.game.state.rng import SeededRng


def test_flush_of_hearts_enter_separates_cast_by_gender() -> None:
    state = new_game(1)

    enter_flush_of_hearts(state)

    assert state.resort is ResortName.FLUSH_OF_HEARTS
    assert state.location_id is Location.FLUSH_POOL
    assert state.flush_of_hearts_state is not None
    assert len(state.flush_of_hearts_state.flush_heartbreaker_ids) == 6


def test_flush_arrival_event_carries_distant_original_partner() -> None:
    state = new_game(1)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]

    event = enter_flush_of_hearts(state)

    assert event.participant_ids == ["player", "chloe"]
    assert "Chloe remains at Sunset Bay" in event.message
    assert "tested at a distance" in event.message


def test_flush_of_hearts_enter_adds_new_heartbreakers() -> None:
    state = new_game(1)

    enter_flush_of_hearts(state)

    ids = {heartbreaker.id for heartbreaker in state.heartbreakers}
    assert {"beau", "jules", "mateo", "sasha", "zara", "noor"} <= ids


def test_flush_of_hearts_display_names_do_not_duplicate_starting_cast() -> None:
    state = new_game(1)
    starting_names = {heartbreaker.name for heartbreaker in state.heartbreakers}

    enter_flush_of_hearts(state)

    flush_names = [
        heartbreaker.name
        for heartbreaker in state.heartbreakers
        if state.flush_of_hearts_state is not None
        and heartbreaker.id in state.flush_of_hearts_state.flush_heartbreaker_ids
    ]
    assert starting_names.isdisjoint(flush_names)
    assert len(flush_names) == len(set(flush_names))


def test_flush_of_hearts_locations_only_visible_at_flush() -> None:
    state = new_game(1)
    enter_flush_of_hearts(state)

    move_targets = {
        spec.action.target_id
        for spec in available_actions(state)
        if spec.action.kind is ActionKind.MOVE
    }

    assert move_targets <= {
        location.value for location in locations_for_resort(ResortName.FLUSH_OF_HEARTS)
    }


def test_resort_main_locations_hidden_at_flush() -> None:
    state = new_game(1)
    enter_flush_of_hearts(state)

    assert Location.POOL not in locations_for_resort(state.resort)
    assert Location.FLUSH_POOL in locations_for_resort(state.resort)


def test_return_with_original_increases_loyalty_perception() -> None:
    state = new_game(1)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]
    enter_flush_of_hearts(state)

    apply_flush_decision(state, FlushDecision.RETURN_WITH_ORIGINAL, "chloe")

    assert state.player.public_perception == 60
    assert state.flush_of_hearts_state is not None
    assert state.flush_of_hearts_state.player_perception_after == 60


def test_return_with_flush_of_hearts_drops_perception_when_original_loyal() -> None:
    state = new_game(1)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]
    enter_flush_of_hearts(state)

    apply_flush_decision(state, FlushDecision.RETURN_WITH_NEW, "beau")
    state.day = 6
    event = return_ceremony(state)

    assert state.player.public_perception == 38
    assert state.flush_of_hearts_state is not None
    assert state.flush_of_hearts_state.partners_swapped is True
    assert state.couples == [
        Couple(
            partner_a_id="player", partner_b_id="beau", formed_on_day=6, formed_via="flush_return"
        )
    ]
    assert event is not None
    assert event.kind == "flush_of_hearts_return_reveal"


def test_return_single_modest_perception_bump() -> None:
    state = new_game(1)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]
    enter_flush_of_hearts(state)

    apply_flush_decision(state, FlushDecision.RETURN_SINGLE, None)

    assert state.player.public_perception == 53


def test_orchestrator_only_sees_same_resort_npcs() -> None:
    state = new_game(1)
    enter_flush_of_hearts(state)

    rendered = _render_context(state)

    assert "beau" in rendered
    assert "chloe" not in rendered


def test_npc_flush_choices_deterministic_from_rng() -> None:
    first = new_game(1)
    second = new_game(1)
    enter_flush_of_hearts(first)
    enter_flush_of_hearts(second)

    assert compute_npc_flush_choices(first, SeededRng(7)) == compute_npc_flush_choices(
        second, SeededRng(7)
    )


def test_eliminated_heartbreakers_dont_return_to_main() -> None:
    state = new_game(1)
    enter_flush_of_hearts(state)
    state.heartbreakers[0].eliminated = True
    state.heartbreakers[0].location_id = Location.FLUSH_POOL
    apply_flush_decision(state, FlushDecision.RETURN_SINGLE, None)

    return_ceremony(state)

    assert state.heartbreakers[0].location_id is Location.FLUSH_POOL


def test_flush_decision_action_is_available_on_day_five_evening() -> None:
    state = new_game(1)
    enter_flush_of_hearts(state)
    state.day = 5
    state.phase = Phase.EVENING

    actions = available_actions(state)

    assert actions
    assert {spec.action.kind for spec in actions} == {ActionKind.FLUSH_DECISION}


def test_resort_update_rejects_cross_resort_movement() -> None:
    state = new_game(1)
    enter_flush_of_hearts(state)
    update = ResortUpdate(
        npc_movements=[
            NPCMovement(npc_id="beau", target_location=Location.POOL, reason="wrong resort")
        ]
    )

    with pytest.raises(ValueError, match="crosses out"):
        validate_resort_update(state, update)


def test_day_four_text_gather_enters_flush_of_hearts() -> None:
    state = new_game(1)
    state.day = 4
    state.phase = Phase.AFTERNOON

    scheduled = run_turn(
        state,
        PlayerAction(kind=ActionKind.AMBIENT, target_id="ambient_wait"),
        SeededRng(1),
        mock_turn_agents(),
    )
    assert scheduled.state.pending_gather is not None
    result = run_turn(
        state, PlayerAction(kind=ActionKind.JOIN_GATHER), SeededRng(1), mock_turn_agents()
    )

    assert result.state.resort is ResortName.FLUSH_OF_HEARTS
    assert any(event.kind == "flush_of_hearts_arrival" for event in result.ceremony_events)
