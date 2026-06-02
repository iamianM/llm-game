"""Tests for NPC interruption validation and responses."""

from __future__ import annotations

import pytest

from src.game.agents.contextual_options import mock_follow_up_menu
from src.game.agents.resort_orchestrator import ResortUpdate
from src.game.engine.actions import ActionKind, PlayerAction, available_actions
from src.game.engine.resort import apply_resort_update, validate_resort_update
from src.game.engine.rules import defer_chance
from src.game.engine.turn import run_turn
from src.game.state.models import Conversation, Location, NPCInterruption, new_game
from src.game.state.rng import SeededRng


def test_orchestrator_can_emit_interruption_in_resort_update() -> None:
    """ResortUpdate schema accepts a single NPC interruption."""
    update = ResortUpdate(
        npc_interruptions=[
            NPCInterruption(interrupter_id="maya", reason="jealous", urgency="insistent")
        ]
    )

    assert update.npc_interruptions[0].interrupter_id == "maya"


def test_resort_update_rejects_two_interruptions_in_one_turn() -> None:
    """Validation rejects more than one interruption."""
    state = _state_with_active_chloe_conversation()
    update = ResortUpdate(
        npc_interruptions=[
            NPCInterruption(interrupter_id="maya", reason="jealous", urgency="insistent"),
            NPCInterruption(interrupter_id="liam", reason="has_gossip", urgency="polite"),
        ]
    )

    with pytest.raises(ValueError, match="one NPC interruption"):
        validate_resort_update(state, update)


def test_resort_update_rejects_interruption_when_no_player_conv() -> None:
    """The Orchestrator cannot interrupt when the player is not talking."""
    state = new_game(1)
    state.heartbreakers[1].location_id = Location.POOL
    update = ResortUpdate(
        npc_interruptions=[
            NPCInterruption(interrupter_id="maya", reason="jealous", urgency="insistent")
        ]
    )

    with pytest.raises(ValueError, match="no active conversation"):
        validate_resort_update(state, update)


def test_resort_update_rejects_interruption_when_one_already_pending() -> None:
    """Only one pending interruption may exist at a time."""
    state = _state_with_active_chloe_conversation()
    state.active_conversation.pending_interruption = NPCInterruption(
        interrupter_id="maya",
        reason="jealous",
        urgency="insistent",
    )
    update = ResortUpdate(
        npc_interruptions=[
            NPCInterruption(interrupter_id="liam", reason="has_gossip", urgency="polite")
        ]
    )

    with pytest.raises(ValueError, match="already pending"):
        validate_resort_update(state, update)


def test_resort_update_rejects_interruption_at_wrong_location() -> None:
    """The interrupter must be co-located with the player."""
    state = _state_with_active_chloe_conversation()
    state.heartbreakers[1].location_id = Location.KITCHEN
    update = ResortUpdate(
        npc_interruptions=[
            NPCInterruption(interrupter_id="maya", reason="jealous", urgency="insistent")
        ]
    )

    with pytest.raises(ValueError, match="not at player location"):
        validate_resort_update(state, update)


def test_apply_resort_update_sets_pending_interruption() -> None:
    """Applying a valid interruption writes it to active conversation state."""
    state = _state_with_active_chloe_conversation()
    update = ResortUpdate(
        npc_interruptions=[
            NPCInterruption(interrupter_id="maya", reason="jealous", urgency="insistent")
        ]
    )

    apply_resort_update(state, update, SeededRng(1))

    assert state.active_conversation is not None
    assert state.active_conversation.pending_interruption is not None


def test_pending_interruption_injects_three_wheel_options() -> None:
    """A pending interruption appears as three code-owned wheel actions."""
    state = _state_with_pending_interruption()

    labels = [spec.label for spec in available_actions(state)]

    assert labels[:3] == [
        "Turn and hear Maya out",
        "Ask Maya for a minute",
        "Ignore Maya and keep talking",
    ]


def test_accept_interruption_closes_current_starts_new() -> None:
    """Welcoming the interrupter changes the active conversation target."""
    state = _state_with_pending_interruption()

    turn = run_turn(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, intent_id="accept_interruption"),
        SeededRng(1),
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )

    assert turn.state.active_conversation is not None
    assert turn.state.active_conversation.target_id == "maya"
    assert turn.mechanical_result.relationship_deltas["chloe"].affection == -2
    assert turn.mechanical_result.relationship_deltas["maya"].affection == 3


def test_defer_interruption_eq_roll_success_path() -> None:
    """Successful deferral mildly annoys the interrupter and keeps current chat."""
    state = _state_with_pending_interruption()
    expected_chance = defer_chance(state, "maya")

    turn = run_turn(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, intent_id="defer_interruption"),
        SeededRng(1),
    )

    assert turn.mechanical_result.success is True
    assert turn.mechanical_result.success_chance == expected_chance
    assert state.active_conversation is not None
    assert state.active_conversation.target_id == "chloe"
    assert state.active_conversation.pending_interruption is None
    assert turn.mechanical_result.relationship_deltas["maya"].affection == -1


def test_defer_interruption_eq_roll_failure_path() -> None:
    """Failed deferral creates a snub memory."""
    state = _state_with_pending_interruption()
    state.player.stats.eq = 3

    turn = run_turn(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, intent_id="defer_interruption"),
        SeededRng(5),
    )

    assert turn.mechanical_result.success is False
    assert turn.mechanical_result.relationship_deltas["maya"].affection == -3
    maya = next(heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == "maya")
    assert any("snubbed_publicly" in memory.tags for memory in maya.memories)


def test_ignore_interruption_keeps_current_drops_affection_4() -> None:
    """Ignoring an interrupter keeps the chat but creates a stronger memory."""
    state = _state_with_pending_interruption()

    turn = run_turn(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, intent_id="ignore_interruption"),
        SeededRng(1),
    )

    assert state.active_conversation is not None
    assert state.active_conversation.target_id == "chloe"
    assert state.active_conversation.pending_interruption is None
    assert turn.mechanical_result.relationship_deltas["maya"].affection == -4
    maya = next(heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == "maya")
    assert any("ignored_in_public" in memory.tags for memory in maya.memories)


def test_ignore_interruption_moves_interrupter_away() -> None:
    state = _state_with_pending_interruption()
    maya = next(heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == "maya")
    before = maya.location_id

    run_turn(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, intent_id="ignore_interruption"),
        SeededRng(1),
    )

    assert maya.location_id != before


def test_ignore_interruption_trace_records_movement() -> None:
    state = _state_with_pending_interruption()

    turn = run_turn(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, intent_id="ignore_interruption"),
        SeededRng(1),
    )

    assert turn.mechanical_result.forced_movements
    movement = turn.mechanical_result.forced_movements[0]
    assert movement.actor_id == "maya"
    assert movement.kind == "walks_away_after_snub"


def _state_with_active_chloe_conversation():
    state = new_game(1)
    state.heartbreakers[1].location_id = Location.POOL
    state.active_conversation = Conversation(
        target_id="chloe",
        started_on_turn=0,
        started_on_day=1,
        pending_options=mock_follow_up_menu(),
    )
    return state


def _state_with_pending_interruption():
    state = _state_with_active_chloe_conversation()
    assert state.active_conversation is not None
    state.active_conversation.pending_interruption = NPCInterruption(
        interrupter_id="maya",
        reason="jealous",
        urgency="insistent",
    )
    return state
