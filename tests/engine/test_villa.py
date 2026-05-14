"""Tests for Villa Orchestrator commit validation and application."""

from __future__ import annotations

import pytest

from src.game.agents.villa_orchestrator import (
    ContinueConversation,
    EndConversation,
    NewConversation,
    NPCMovement,
    VillaUpdate,
)
from src.game.engine.villa import apply_villa_update, normalize_villa_update, validate_villa_update
from src.game.state.models import Location, NPCNPCConversation, PendingGather, new_game
from src.game.state.rng import SeededRng


def test_villa_update_rejects_eliminated_npc() -> None:
    """The Orchestrator cannot use eliminated islanders."""
    state = new_game(1)
    state.islanders[0].eliminated = True
    update = VillaUpdate(
        npc_movements=[NPCMovement(npc_id="chloe", target_location=Location.POOL, reason="drift")]
    )

    with pytest.raises(ValueError, match="eliminated"):
        validate_villa_update(state, update)


def test_villa_update_rejects_player_in_npc_conv() -> None:
    """NPC-NPC conversations never include the player."""
    state = new_game(1)
    update = VillaUpdate(
        conversation_starts=[
            NewConversation(participants=["player", "chloe"], location=Location.POOL, topic="bad")
        ]
    )

    with pytest.raises(ValueError, match="player"):
        validate_villa_update(state, update)


def test_villa_update_rejects_start_at_wrong_location() -> None:
    """Starts require both NPCs to be co-located after movements apply."""
    state = new_game(1)
    update = VillaUpdate(
        conversation_starts=[
            NewConversation(
                participants=["chloe", "maya"],
                location=Location.POOL,
                topic="comparing notes",
            )
        ]
    )

    with pytest.raises(ValueError, match="not at location"):
        validate_villa_update(state, update)


def test_villa_update_rejects_end_and_continue_same_conv() -> None:
    """A conversation cannot both continue and end in one update."""
    state = new_game(1)
    state.npc_conversations.append(_npc_conversation())
    update = VillaUpdate(
        conversation_continues=[ContinueConversation(conversation_id="npcconv_test")],
        conversation_ends=[EndConversation(conversation_id="npcconv_test", reason="natural_end")],
    )

    with pytest.raises(ValueError, match="end and continue"):
        validate_villa_update(state, update)


def test_villa_update_rejects_movement_during_pending_gather() -> None:
    """Autonomy pauses while mandatory gather actions are waiting."""
    state = new_game(1)
    state.pending_gather = PendingGather(
        kind="ceremony",
        event_id="recoupling_day_3",
        gather_location=Location.FIREPIT,
        fires_on_turn=1,
    )
    update = VillaUpdate(
        npc_movements=[NPCMovement(npc_id="chloe", target_location=Location.KITCHEN, reason="drift")]
    )

    with pytest.raises(ValueError, match="gather is pending"):
        validate_villa_update(state, update)


def test_apply_movements_updates_locations() -> None:
    """Validated movement commits mutate NPC location."""
    state = new_game(1)
    update = VillaUpdate(
        npc_movements=[NPCMovement(npc_id="maya", target_location=Location.POOL, reason="joining")]
    )

    apply_villa_update(state, update, SeededRng(1))

    assert state.islanders[1].location_id is Location.POOL


def test_moving_conversation_participant_implies_conversation_end() -> None:
    state = new_game(1)
    conversation = _npc_conversation()
    state.npc_conversations.append(conversation)
    update = VillaUpdate(
        npc_movements=[NPCMovement(npc_id="chloe", target_location=Location.KITCHEN, reason="drift")],
        conversation_continues=[ContinueConversation(conversation_id=conversation.id)],
    )

    normalized = normalize_villa_update(state, update)

    validate_villa_update(state, normalized)
    assert normalized.conversation_continues == []
    assert normalized.conversation_ends[0].conversation_id == conversation.id
    assert normalized.conversation_ends[0].reason == "participant_moved"


def test_stale_conversation_location_implies_conversation_end() -> None:
    state = new_game(1)
    conversation = _npc_conversation()
    state.npc_conversations.append(conversation)
    state.islanders[0].location_id = Location.KITCHEN

    normalized = normalize_villa_update(state, VillaUpdate())

    validate_villa_update(state, normalized)
    assert normalized.conversation_ends[0].conversation_id == conversation.id


def test_npc_conversation_close_invokes_curator() -> None:
    """Closing an NPC-NPC conversation creates memories for participants."""
    state = new_game(1)
    conversation = _npc_conversation()
    state.npc_conversations.append(conversation)
    update = VillaUpdate(
        conversation_ends=[EndConversation(conversation_id=conversation.id, reason="natural_end")]
    )

    changes = apply_villa_update(state, update, SeededRng(1))

    assert changes.curator_batches
    assert changes.curator_batches[0].kind == "background"
    assert state.npc_conversations == []
    assert state.islanders[0].memories
    assert state.islanders[1].memories


def test_conversation_start_creates_background_exchange() -> None:
    """Starting a background conversation creates persistent state and an exchange."""
    state = new_game(1)
    state.islanders[1].location_id = Location.POOL
    update = VillaUpdate(
        conversation_starts=[
            NewConversation(
                participants=["chloe", "maya"],
                location=Location.POOL,
                topic="gossip about the morning",
            )
        ]
    )

    changes = apply_villa_update(state, update, SeededRng(1))

    assert len(state.npc_conversations) == 1
    assert len(state.npc_conversations[0].exchanges) == 1
    assert len(changes.background_dialogues) == 1


def _npc_conversation() -> NPCNPCConversation:
    return NPCNPCConversation(
        id="npcconv_test",
        participants=["chloe", "maya"],
        location_id=Location.POOL,
        topic="a private chat",
        started_on_turn=1,
    )
