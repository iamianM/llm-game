"""Tests for the one-turn pipeline."""

from __future__ import annotations

from src.game.agents.contextual_options import mock_follow_up_menu
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.memory import add_memory, create_memory
from src.game.engine.rules import apply_action
from src.game.engine.turn import run_turn
from src.game.state.models import (
    Location,
    MemoryBatch,
    MemoryDraft,
    NPCNPCConversation,
    PendingGather,
    Phase,
    new_game,
)
from src.game.state.rng import SeededRng


def test_run_turn_applies_action_and_returns_next_actions() -> None:
    """A turn mutates state once and returns the next valid action surface."""
    state = new_game(1)

    result = run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(1),
    )

    assert result.state.turn_index == 1
    assert result.state.islanders[0].relationship.affection == 12
    assert result.exchange is not None
    assert result.exchange.npc_dialogue
    assert result.available_actions
    assert len(result.state_hash) == 64


def test_run_turn_advances_phase() -> None:
    """ADVANCE_PHASE uses the same run_turn path as other actions."""
    state = new_game(1)

    result = run_turn(state, PlayerAction(kind=ActionKind.ADVANCE_PHASE), SeededRng(1))

    assert result.state.phase is Phase.CHALLENGE
    assert result.state.turn_index == 1


def test_run_turn_schedules_casa_amor_arrival_as_gather() -> None:
    """Producer texts schedule a mandatory gather before Casa Amor resolves."""
    state = new_game(1)
    state.day = 4
    state.phase = Phase.AFTERNOON

    result = run_turn(state, PlayerAction(kind=ActionKind.ADVANCE_PHASE), SeededRng(1))

    assert result.state.phase is Phase.TEXT
    assert result.state.pending_gather is not None
    assert result.state.pending_gather.kind == "casa_announce"
    assert [spec.action.kind for spec in result.available_actions] == [ActionKind.JOIN_GATHER]


def test_run_turn_skips_villa_autonomy_after_scheduling_gather() -> None:
    """The turn that schedules a mandatory gather does not call Orchestrator."""
    state = new_game(1)
    state.day = 4
    state.phase = Phase.AFTERNOON

    def fail_orchestrator(_state):
        raise AssertionError("villa autonomy should pause while gather is pending")

    result = run_turn(
        state,
        PlayerAction(kind=ActionKind.ADVANCE_PHASE),
        SeededRng(1),
        villa_orchestrator=fail_orchestrator,
    )

    assert result.state.pending_gather is not None
    assert result.agent_commits.villa_update is not None
    assert result.agent_commits.villa_update.npc_movements == []


def test_join_gather_resolves_casa_amor_arrival() -> None:
    """JOIN_GATHER moves the villa to the firepit and then resolves the event."""
    state = new_game(1)
    state.day = 4
    state.phase = Phase.AFTERNOON
    run_turn(state, PlayerAction(kind=ActionKind.ADVANCE_PHASE), SeededRng(1))

    result = run_turn(state, PlayerAction(kind=ActionKind.JOIN_GATHER), SeededRng(2))

    assert any(event.kind == "casa_amor_arrival" for event in result.ceremony_events)
    assert result.state.pending_gather is None
    assert result.state.casa_amor_state is not None
    assert result.event_narration is not None


def test_join_gather_closes_active_and_background_conversations() -> None:
    """Mandatory gathers clear conversations before event narration."""
    state = new_game(1)
    rng = SeededRng(1)
    run_turn(
        state,
        PlayerAction(kind=ActionKind.START_CONVERSATION, target_id="chloe", intent_id="friendly_chat_villa"),
        rng,
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )
    state.npc_conversations.append(
        NPCNPCConversation(
            id="npcconv_test",
            participants=["maya", "liam"],
            location_id=Location.TERRACE,
            topic="quiet strategy",
            started_on_turn=state.turn_index,
        )
    )
    state.pending_gather = PendingGather(
        kind="ceremony",
        event_id="recoupling_day_3",
        gather_location=Location.FIREPIT,
        fires_on_turn=state.turn_index + 1,
    )
    state.day = 3
    state.phase = Phase.EVENING

    result = run_turn(state, PlayerAction(kind=ActionKind.JOIN_GATHER), rng)

    assert result.state.active_conversation is None
    assert result.state.npc_conversations == []
    assert all(islander.location_id is not Location.TERRACE for islander in result.state.islanders)
    assert result.curator_batches


def test_daily_recap_generated_at_day_rollover() -> None:
    """Day rollover appends a recap from notable memories."""
    state = new_game(1)
    state.day = 1
    state.phase = Phase.EVENING
    add_memory(
        state,
        create_memory(
            holder_id="chloe",
            subject_id="maya",
            source="witnessed",
            day=1,
            turn=0,
            weight=9,
            tags=["background"],
            content="Maya and Liam had a sharp terrace moment.",
        ),
    )

    result = run_turn(state, PlayerAction(kind=ActionKind.ADVANCE_PHASE), SeededRng(1))

    assert result.state.day == 2
    assert result.state.daily_recaps
    assert result.state.daily_recaps[0].items[0].content == "Maya and Liam had a sharp terrace moment."


def test_apply_action_does_not_bump_turn_index() -> None:
    """Turn bookkeeping only happens inside run_turn."""
    state = new_game(1)

    apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(1),
    )

    assert state.turn_index == 0


def test_wheel_exit_closes_conversation_and_applies_trust_bonus() -> None:
    """A wheel exit produces a goodbye exchange, curates, and closes."""
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
    calls = 0

    def curator(*_args) -> MemoryBatch:
        nonlocal calls
        calls += 1
        return MemoryBatch(
            memories=[
                MemoryDraft(
                    holder_id="player",
                    subject_id="chloe",
                    content="I ended the chat warmly.",
                    source="direct",
                    emotional_weight=3,
                    tags=["exit"],
                )
            ]
        )

    result = run_turn(
        state,
        PlayerAction(kind=ActionKind.RESPOND_WITH, intent_id="end_softly"),
        rng,
        contextual_options=lambda *_args: mock_follow_up_menu(),
        conversation_curator=curator,
    )

    assert result.exchange is not None
    assert result.state.active_conversation is None
    assert result.mechanical_result.relationship_deltas["chloe"].trust == 1
    assert calls == 1
    assert result.curator_batches


def test_walk_away_closes_conversation_and_applies_affection_penalty() -> None:
    """Top-level END_CONVERSATION is a curt walk-away, not a graceful wheel exit."""
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
    affection_before = state.islanders[0].relationship.affection
    calls = 0

    def curator(*_args) -> MemoryBatch:
        nonlocal calls
        calls += 1
        return MemoryBatch(
            memories=[
                MemoryDraft(
                    holder_id="player",
                    subject_id="chloe",
                    content="I walked away from the chat.",
                    source="direct",
                    emotional_weight=4,
                    tags=["walked_away"],
                )
            ]
        )

    result = run_turn(
        state,
        PlayerAction(kind=ActionKind.END_CONVERSATION),
        rng,
        conversation_curator=curator,
    )

    assert result.exchange is None
    assert result.state.active_conversation is None
    assert state.islanders[0].relationship.affection == affection_before - 1
    assert result.mechanical_result.relationship_deltas["chloe"].affection == -1
    assert calls == 1
    assert result.curator_batches
