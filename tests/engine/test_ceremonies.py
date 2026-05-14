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
