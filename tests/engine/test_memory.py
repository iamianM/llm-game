"""Tests for deterministic memory storage."""

from __future__ import annotations

from dataclasses import replace

from src.game.agents.contextual_options import mock_follow_up_menu
from src.game.agents.turn_agents import mock_turn_agents
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.memory import add_memory_batch, create_memory
from src.game.engine.turn import run_turn
from src.game.state.memory import RecapDisposition
from src.game.state.models import MemoryBatch, MemoryDraft, Phase, new_game
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
            intent_id="friendly_chat_resort",
        ),
        rng,
        replace(
            mock_turn_agents(),
            contextual_options=lambda *_args: mock_follow_up_menu(),
        ),
    )

    run_turn(state, PlayerAction(kind=ActionKind.END_CONVERSATION), rng, mock_turn_agents())

    assert state.player.memories
    assert state.player.memories[0].holder_id == "player"
    assert state.player.memories[0].subject_id == "chloe"
    assert state.heartbreakers[0].memories
    assert state.heartbreakers[0].memories[0].holder_id == "chloe"
    assert state.heartbreakers[0].memories[0].subject_id == "player"


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
        recap_disposition=RecapDisposition.NONE,
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
        recap_disposition=RecapDisposition.NONE,
    )

    assert first.id == second.id


def test_ceremony_memory_is_witnessed() -> None:
    """Ceremony events create witnessed memories for the resort."""
    state = new_game(1)
    state.day = 3
    state.phase = Phase.EVENING

    run_turn(
        state,
        PlayerAction(kind=ActionKind.AMBIENT, target_id="ambient_wait"),
        SeededRng(1),
        mock_turn_agents(),
    )

    assert any(memory.source == "witnessed" for memory in state.player.memories)


def test_engine_batch_context_assigns_recap_disposition() -> None:
    state = new_game(1)
    draft = MemoryDraft(
        holder_id="player",
        subject_id=state.heartbreakers[0].id,
        content="The player had a meaningful conversation.",
        source="direct",
        emotional_weight=6,
    )

    player_memory = add_memory_batch(
        state,
        MemoryBatch(kind="player", memories=[draft]),
        day=1,
        turn=1,
    )[0]
    background_memory = add_memory_batch(
        state,
        MemoryBatch(
            kind="background",
            memories=[draft.model_copy(update={"holder_id": state.heartbreakers[1].id})],
        ),
        day=1,
        turn=2,
    )[0]

    assert player_memory.recap_disposition is RecapDisposition.YOUR_DAY
    assert background_memory.recap_disposition is RecapDisposition.WHILE_BUSY
