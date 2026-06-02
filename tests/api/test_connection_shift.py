"""Tests for the per-turn Connection shift line surfaced on TurnResponse.

`connection_shift_line` is the API-boundary glue between the engine's raw
``relationship_deltas`` map and the pure :func:`describe_shift` phrasing. It owns
one editorial decision: surface a line only for the *acted-on* heartbreaker
(``action.target_id``), so the player reads how the relationship they were
steering moved — not every secondary ripple the turn produced.
"""

from __future__ import annotations

from src.api.serializers import connection_shift_line
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.results import MechanicalResult
from src.game.state.models import RelationshipDelta, new_game


def _state():
    """A fresh deterministic resort; heartbreaker ids/names are stable for seed 42."""
    return new_game(42)


def _result(target_id, deltas) -> MechanicalResult:
    return MechanicalResult(
        action=PlayerAction(kind=ActionKind.RESPOND_WITH, target_id=target_id),
        success=True,
        relationship_deltas=deltas,
    )


def test_line_names_the_acted_on_heartbreaker() -> None:
    state = _state()
    target = state.heartbreakers[0]
    result = _result(target.id, {target.id: RelationshipDelta(chemistry=9)})
    line = connection_shift_line(state, result)
    assert line is not None
    assert target.name in line
    assert "spark" in line.lower()


def test_idle_move_with_no_target_yields_nothing() -> None:
    state = _state()
    result = MechanicalResult(
        action=PlayerAction(kind=ActionKind.MOVE, target_id=None),
        success=True,
        relationship_deltas={},
    )
    assert connection_shift_line(state, result) is None


def test_player_target_is_never_a_shift_line() -> None:
    # A bond change credited to "player" is not a relationship the player steers
    # toward another heartbreaker, so it must not produce a headline.
    state = _state()
    result = _result("player", {"player": RelationshipDelta(trust=8)})
    assert connection_shift_line(state, result) is None


def test_target_without_a_delta_entry_yields_nothing() -> None:
    # The action named a target but the resolution moved no bond for them.
    state = _state()
    target = state.heartbreakers[0]
    assert connection_shift_line(state, _result(target.id, {})) is None


def test_only_the_targets_delta_is_reported_not_secondary_ripples() -> None:
    # A turn can move several heartbreakers (e.g. a bystander reacts). The headline
    # tracks the acted-on heartbreaker only, ignoring the bigger swing elsewhere.
    state = _state()
    target = state.heartbreakers[0]
    bystander = state.heartbreakers[1]
    result = _result(
        target.id,
        {
            target.id: RelationshipDelta(chemistry=3),
            bystander.id: RelationshipDelta(affection=10),
        },
    )
    line = connection_shift_line(state, result)
    assert line is not None
    assert target.name in line
    assert bystander.name not in line


def test_net_zero_target_delta_yields_nothing() -> None:
    # A delta object that nets to no movement should not surface empty feedback.
    state = _state()
    target = state.heartbreakers[0]
    assert connection_shift_line(state, _result(target.id, {target.id: RelationshipDelta()})) is None
