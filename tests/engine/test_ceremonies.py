"""Tests for deterministic ceremony mechanics."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.ceremonies import arrive_bombshell, recoupling
from src.game.engine.rules import apply_action
from src.game.state.models import Gender, new_game
from src.game.state.rng import SeededRng


def test_recoupling_pairs_player_with_top_relationship() -> None:
    """Player gets the highest-scored active islander."""
    state = new_game(1)
    state.islanders[1].relationship.affection = 40

    result = recoupling(state)

    assert result.couples[0].partner_a_id == "player"
    assert result.couples[0].partner_b_id == "maya"


def test_recoupling_eliminates_leftover_islander() -> None:
    """An odd active cast leaves one islander dumped."""
    state = new_game(1)
    state.islanders[-1].eliminated = True
    arrive_bombshell(state)

    result = recoupling(state)

    assert result.eliminated_id is not None
    assert any(islander.eliminated for islander in state.islanders)


def test_recoupling_keeps_npc_couples_opposite_gender() -> None:
    """Later ceremony matching uses the same gender constraint as opening coupling."""
    state = new_game(1)
    state.day = 3
    state.player.gender = Gender.MAN
    for islander in state.islanders:
        islander.relationship.affection = 10
        islander.relationship.chemistry = 10
        islander.relationship.trust = 10

    result = recoupling(state, "chloe")

    genders = {islander.id: islander.gender for islander in state.islanders}
    genders[state.player.id] = state.player.gender
    for couple in result.couples:
        assert genders[couple.partner_a_id] != genders[couple.partner_b_id]


def test_recoupling_rejects_same_gender_player_choice() -> None:
    """A player cannot choose a same-gender recoupling partner in v0."""
    state = new_game(1)
    state.day = 3
    state.player.gender = Gender.MAN

    try:
        recoupling(state, "liam")
    except ValueError as exc:
        assert "opposite sex" in str(exc)
    else:
        raise AssertionError("same-gender recoupling choice should fail")


def test_bombshell_arrival_is_idempotent() -> None:
    """The day-four bombshell is inserted once."""
    state = new_game(1)

    first = arrive_bombshell(state)
    second = arrive_bombshell(state)

    assert first.id == "aisha"
    assert second.id == "aisha"
    assert [islander.id for islander in state.islanders].count("aisha") == 1


def test_recoupling_pick_surfaces_eligible_partners() -> None:
    """When a recoupling gather is pending, the action menu offers partner picks."""
    from src.game.engine.actions import available_actions
    from src.game.state.models import PendingGather, Location

    state = new_game(2)
    state.day = 3
    state.player.gender = Gender.MAN
    state.pending_gather = PendingGather(
        kind="ceremony",
        event_id="recoupling_day_3",
        gather_location=Location.FIREPIT,
        fires_on_turn=state.turn_index,
    )
    state.location_id = Location.FIREPIT

    actions = available_actions(state)

    # Every action should be RECOUPLE (no JOIN_GATHER) and target an
    # opposite-sex islander.
    kinds = {spec.action.kind for spec in actions}
    assert kinds == {ActionKind.RECOUPLE}
    targets = {spec.action.target_id for spec in actions}
    expected_women = {
        islander.id
        for islander in state.islanders
        if islander.gender == Gender.WOMAN and not islander.eliminated
    }
    assert targets == expected_women


def test_recoupling_pick_applies_player_choice() -> None:
    """Applying a RECOUPLE during a pending recoupling gather resolves it."""
    from src.game.engine.turn import run_turn
    from src.game.state.models import PendingGather, Location

    state = new_game(2)
    state.day = 3
    state.player.gender = Gender.MAN
    state.phase_clock.elapsed_minutes = state.phase_clock.budget_minutes
    from src.game.state.models import Phase
    state.phase = Phase.EVENING
    state.pending_gather = PendingGather(
        kind="ceremony",
        event_id="recoupling_day_3",
        gather_location=Location.FIREPIT,
        fires_on_turn=state.turn_index,
    )
    state.location_id = Location.FIREPIT

    # Pick Maya (any opposite-sex islander)
    turn = run_turn(
        state,
        PlayerAction(kind=ActionKind.RECOUPLE, target_id="maya"),
        SeededRng(99),
    )

    assert turn.state.pending_gather is None
    player_couple = next(
        couple
        for couple in turn.state.couples
        if "player" in {couple.partner_a_id, couple.partner_b_id}
    )
    other = (
        player_couple.partner_b_id
        if player_couple.partner_a_id == "player"
        else player_couple.partner_a_id
    )
    assert other == "maya"


def test_public_perception_bounds() -> None:
    """Perception changes stay in the 0-100 range."""
    state = new_game(1)
    state.player.public_perception = 1

    state.islanders[0].relationship.affection = 20
    apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="flirty_compliment_looks",
        ),
        SeededRng(19),
    )

    assert state.player.public_perception == 0
