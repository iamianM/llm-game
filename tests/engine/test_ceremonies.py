"""Tests for deterministic ceremony mechanics."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.ceremonies import arrive_bombshell, recoupling
from src.game.engine.rules import apply_action
from src.game.state.models import new_game
from src.game.state.rng import SeededRng


def test_recoupling_pairs_player_with_top_relationship() -> None:
    """Player gets the highest-scored active islander."""
    state = new_game(1)
    state.islanders[1].relationship.affection = 40

    result = recoupling(state, SeededRng(1))

    assert result.couples[0].partner_a_id == "player"
    assert result.couples[0].partner_b_id == "maya"


def test_recoupling_eliminates_leftover_islander() -> None:
    """An odd active cast leaves one islander dumped."""
    state = new_game(1)
    arrive_bombshell(state, SeededRng(1))

    result = recoupling(state, SeededRng(1))

    assert result.eliminated_id is not None
    assert any(islander.eliminated for islander in state.islanders)


def test_bombshell_arrival_is_idempotent() -> None:
    """The day-four bombshell is inserted once."""
    state = new_game(1)

    first = arrive_bombshell(state, SeededRng(1))
    second = arrive_bombshell(state, SeededRng(99))

    assert first.id == "aisha"
    assert second.id == "aisha"
    assert [islander.id for islander in state.islanders].count("aisha") == 1


def test_public_perception_bounds() -> None:
    """Perception changes stay in the 0-100 range."""
    state = new_game(1)
    state.player.public_perception = 1

    apply_action(state, PlayerAction(kind=ActionKind.BOLD_FLIRT, target_id="chloe"), SeededRng(5))

    assert state.player.public_perception == 0
