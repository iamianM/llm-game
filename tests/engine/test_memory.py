"""Tests for deterministic memory storage."""

from __future__ import annotations

from src.game.agents.contextual_options import mock_follow_up_menu
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.memory import create_memory
from src.game.engine.turn import run_turn
from src.game.state.models import Phase, new_game
from src.game.state.rng import SeededRng


def test_conversation_close_creates_memories() -> None:
    """Closing a conversation records it for the player and target."""
    state = new_game(1)
    rng = SeededRng(1)
    run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        rng,
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )

    run_turn(state, PlayerAction(kind=ActionKind.END_CONVERSATION), rng)

    assert state.player.memories
    assert state.player.memories[0].holder_id == "player"
    assert state.player.memories[0].subject_id == "chloe"
    assert state.islanders[0].memories
    assert state.islanders[0].memories[0].holder_id == "chloe"
    assert state.islanders[0].memories[0].subject_id == "player"


def test_memory_id_deterministic_from_fields() -> None:
    """Same memory metadata yields the same id."""
    first = create_memory(
        holder_id="chloe",
        subject_id="player",
        source="direct",
        day=1,
        turn=2,
        weight=4,
        tags=["friendly", "warm"],
        content="First wording.",
    )
    second = create_memory(
        holder_id="chloe",
        subject_id="player",
        source="direct",
        day=1,
        turn=2,
        weight=4,
        tags=["warm", "friendly"],
        content="Second wording.",
    )

    assert first.id == second.id


def test_ceremony_memory_is_witnessed() -> None:
    """Ceremony events create witnessed memories for the villa."""
    state = new_game(1)
    state.day = 3
    state.phase = Phase.EVENING

    run_turn(state, PlayerAction(kind=ActionKind.ADVANCE_PHASE), SeededRng(1))

    assert any(memory.source == "witnessed" for memory in state.player.memories)
