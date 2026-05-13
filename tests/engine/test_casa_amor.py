"""Tests for Casa Amor flow."""

from __future__ import annotations

import pytest

from src.game.agents.villa_orchestrator import NPCMovement, VillaUpdate, _render_context
from src.game.engine.actions import ActionKind, PlayerAction, available_actions
from src.game.engine.casa_amor import (
    apply_casa_decision,
    compute_npc_casa_choices,
    enter_casa_amor,
    locations_for_villa,
    return_ceremony,
)
from src.game.engine.turn import run_turn
from src.game.engine.villa import validate_villa_update
from src.game.state.casa import CasaDecision, VillaName
from src.game.state.models import Couple, Location, Phase, new_game
from src.game.state.rng import SeededRng


def test_casa_amor_enter_separates_cast_by_gender() -> None:
    state = new_game(1)

    enter_casa_amor(state)

    assert state.villa is VillaName.CASA_AMOR
    assert state.location_id is Location.CASA_POOL
    assert state.casa_amor_state is not None
    assert len(state.casa_amor_state.casa_islander_ids) == 6


def test_casa_amor_enter_adds_new_islanders() -> None:
    state = new_game(1)

    enter_casa_amor(state)

    ids = {islander.id for islander in state.islanders}
    assert {"blake", "jordan", "marcus", "sophie", "zara", "nia"} <= ids


def test_casa_amor_locations_only_visible_at_casa() -> None:
    state = new_game(1)
    enter_casa_amor(state)

    move_targets = {
        spec.action.target_id
        for spec in available_actions(state)
        if spec.action.kind is ActionKind.MOVE
    }

    assert move_targets <= {location.value for location in locations_for_villa(VillaName.CASA_AMOR)}


def test_villa_main_locations_hidden_at_casa() -> None:
    state = new_game(1)
    enter_casa_amor(state)

    assert Location.POOL not in locations_for_villa(state.villa)
    assert Location.CASA_POOL in locations_for_villa(state.villa)


def test_return_with_original_increases_loyalty_perception() -> None:
    state = new_game(1)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]
    enter_casa_amor(state)

    apply_casa_decision(state, CasaDecision.RETURN_WITH_ORIGINAL, "chloe")

    assert state.player.public_perception == 60
    assert state.casa_amor_state is not None
    assert state.casa_amor_state.player_perception_after == 60


def test_return_with_casa_amor_drops_perception_when_original_loyal() -> None:
    state = new_game(1)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]
    enter_casa_amor(state)

    apply_casa_decision(state, CasaDecision.RETURN_WITH_NEW, "blake")
    state.day = 6
    event = return_ceremony(state)

    assert state.player.public_perception == 38
    assert state.casa_amor_state is not None
    assert state.casa_amor_state.partners_swapped is True
    assert state.couples == [Couple(partner_a_id="player", partner_b_id="blake", formed_on_day=6)]
    assert event is not None
    assert event.kind == "casa_amor_return_reveal"


def test_return_single_modest_perception_bump() -> None:
    state = new_game(1)
    state.couples = [Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1)]
    enter_casa_amor(state)

    apply_casa_decision(state, CasaDecision.RETURN_SINGLE, None)

    assert state.player.public_perception == 53


def test_orchestrator_only_sees_same_villa_npcs() -> None:
    state = new_game(1)
    enter_casa_amor(state)

    rendered = _render_context(state)

    assert "blake" in rendered
    assert "chloe" not in rendered


def test_npc_casa_choices_deterministic_from_rng() -> None:
    first = new_game(1)
    second = new_game(1)
    enter_casa_amor(first)
    enter_casa_amor(second)

    assert compute_npc_casa_choices(first, SeededRng(7)) == compute_npc_casa_choices(second, SeededRng(7))


def test_eliminated_islanders_dont_return_to_main() -> None:
    state = new_game(1)
    enter_casa_amor(state)
    state.islanders[0].eliminated = True
    state.islanders[0].location_id = Location.CASA_POOL
    apply_casa_decision(state, CasaDecision.RETURN_SINGLE, None)

    return_ceremony(state)

    assert state.islanders[0].location_id is Location.CASA_POOL


def test_casa_decision_action_is_available_on_day_five_evening() -> None:
    state = new_game(1)
    enter_casa_amor(state)
    state.day = 5
    state.phase = Phase.EVENING

    actions = available_actions(state)

    assert actions
    assert {spec.action.kind for spec in actions} == {ActionKind.CASA_DECISION}


def test_villa_update_rejects_cross_villa_movement() -> None:
    state = new_game(1)
    enter_casa_amor(state)
    update = VillaUpdate(
        npc_movements=[NPCMovement(npc_id="blake", target_location=Location.POOL, reason="wrong villa")]
    )

    with pytest.raises(ValueError, match="crosses out"):
        validate_villa_update(state, update)


def test_day_four_text_advance_enters_casa_amor() -> None:
    state = new_game(1)
    state.day = 4
    state.phase = Phase.TEXT

    result = run_turn(state, PlayerAction(kind=ActionKind.ADVANCE_PHASE), SeededRng(1))

    assert result.state.villa is VillaName.CASA_AMOR
    assert any(event.kind == "casa_amor_arrival" for event in result.ceremony_events)
