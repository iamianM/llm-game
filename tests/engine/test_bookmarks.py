"""Tests for deterministic trace bookmarks."""

from __future__ import annotations

from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.bookmarks import bookmarks_for_turn
from src.game.engine.results import MechanicalResult
from src.game.engine.turn import TurnResult
from src.game.state.models import GameState, new_game
from src.game.state.snapshot import state_hash, state_hash_payload


def test_auto_bookmark_for_auto_advance() -> None:
    state = new_game(1)
    turn = _turn(state, auto_advance=True)

    bookmarks = bookmarks_for_turn(turn)

    assert bookmarks[0].kind == "auto_advance"
    assert bookmarks[0].category == "event"


def _turn(state: GameState, *, auto_advance: bool = False) -> TurnResult:
    result = MechanicalResult(
        action=PlayerAction(kind=ActionKind.AMBIENT, target_id="ambient_wait"),
        success=True,
        relationship_deltas={},
    )
    return TurnResult(
        state=state,
        mechanical_result=result,
        available_actions=[],
        state_hash=state_hash(state_hash_payload(state)),
        auto_advance=auto_advance,
    )
