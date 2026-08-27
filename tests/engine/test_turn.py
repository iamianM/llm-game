"""Tests for the one-turn pipeline."""

from __future__ import annotations

from dataclasses import replace

import pytest

from src.game.agents.contextual_options import mock_follow_up_menu
from src.game.agents.runtime import (
    AgentGenerationError,
    AgentValidationError,
    record_agent_trace,
    recover_agent_traces_after_error,
)
from src.game.agents.turn_agents import mock_turn_agents
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.ceremonies import CeremonyEvent
from src.game.engine.memory import add_memory, create_memory
from src.game.engine.rules import apply_action
from src.game.engine.turn import _narrated_events, run_turn
from src.game.state.memory import RecapDisposition
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
from src.game.state.snapshot import state_hash, state_hash_payload

MOCK_AGENTS = mock_turn_agents()
FOLLOW_UP_AGENTS = replace(MOCK_AGENTS, contextual_options=lambda *_args: mock_follow_up_menu())


def test_run_turn_applies_action_and_returns_next_actions() -> None:
    """A turn mutates state once and returns the next valid action surface."""
    state = new_game(1)

    result = run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        SeededRng(1),
        MOCK_AGENTS,
    )

    assert result.state.turn_index == 1
    assert result.state.heartbreakers[0].relationship.affection == 12
    assert result.exchange is not None
    assert result.exchange.npc_dialogue
    assert result.available_actions
    assert len(result.state_hash) == 64


def test_run_turn_rolls_back_state_and_rng_on_agent_failure() -> None:
    """A failed story port leaves both caller-owned deterministic inputs unchanged."""
    state = new_game(1)
    rng = SeededRng(1)
    state_before = state_hash(state_hash_payload(state))
    rng_before = rng.snapshot()

    def boom(*_args, **_kwargs):
        record_agent_trace(
            agent_name="heartbreaker_voice",
            model="test-model",
            prompt_path="test",
            response=object(),
            output=None,
        )
        raise AgentValidationError("heartbreaker voice exhausted retries")

    with pytest.raises(AgentValidationError, match="exhausted retries"):
        run_turn(
            state,
            PlayerAction(
                kind=ActionKind.START_CONVERSATION,
                target_id="chloe",
                intent_id="friendly_chat_resort",
            ),
            rng,
            replace(MOCK_AGENTS, heartbreaker_voice=boom),
        )

    assert state_hash(state_hash_payload(state)) == state_before
    assert rng.snapshot() == rng_before
    traces = recover_agent_traces_after_error()
    assert [trace.agent_name for trace in traces] == ["heartbreaker_voice"]


def test_run_turn_rolls_back_non_agent_error_from_story_port() -> None:
    """Atomic rollback also protects the caller from unexpected adapter bugs."""
    state = new_game(1)
    rng = SeededRng(1)
    state_before = state_hash(state_hash_payload(state))
    rng_before = rng.snapshot()

    def kaboom(*_args, **_kwargs):
        raise KeyError("genuine engine bug, not an agent failure")

    with pytest.raises(KeyError):
        run_turn(
            state,
            PlayerAction(
                kind=ActionKind.START_CONVERSATION,
                target_id="chloe",
                intent_id="friendly_chat_resort",
            ),
            rng,
            replace(MOCK_AGENTS, heartbreaker_voice=kaboom),
        )

    assert state_hash(state_hash_payload(state)) == state_before
    assert rng.snapshot() == rng_before


def test_narrated_events_propagates_event_narrator_raise() -> None:
    """The event narrator port fails loud for the atomic boundary to handle."""
    from src.game.engine.ceremonies import CeremonyEvent
    from src.game.engine.turn import _narrated_events

    state = new_game(1)
    events = [CeremonyEvent(kind="pairing", message="Chloe was chosen.", heartbreaker_id="chloe")]

    def boom(*_args, **_kwargs):
        raise AgentGenerationError("event narrator exhausted retries")

    with pytest.raises(AgentGenerationError, match="event narrator exhausted retries"):
        _narrated_events(state, events, boom)


def test_run_turn_ambient_wait_advances_phase() -> None:
    """Ambient wait burns the morning budget; the round-based Day-1 quiz then
    holds the phase on CHALLENGE until the player answers all five rounds."""
    state = new_game(1)

    result = run_turn(
        state,
        PlayerAction(kind=ActionKind.AMBIENT, target_id="ambient_wait"),
        SeededRng(1),
        MOCK_AGENTS,
    )

    assert result.state.phase is Phase.CHALLENGE
    assert result.state.pending_challenge is not None
    assert result.state.pending_challenge.kind == "compatibility_quiz"
    assert len(result.state.pending_challenge.rounds) == 5
    assert result.state.turn_index == 1


def test_run_turn_schedules_flush_of_hearts_arrival_as_gather() -> None:
    """Producer texts schedule a mandatory gather before Flush of Hearts resolves."""
    state = new_game(1)
    state.day = 4
    state.phase = Phase.AFTERNOON

    result = run_turn(
        state,
        PlayerAction(kind=ActionKind.AMBIENT, target_id="ambient_wait"),
        SeededRng(1),
        MOCK_AGENTS,
    )

    assert result.state.phase is Phase.TEXT
    assert result.state.pending_gather is not None
    assert result.state.pending_gather.kind == "flush_announce"
    assert [spec.action.kind for spec in result.available_actions] == [ActionKind.JOIN_GATHER]


def test_run_turn_skips_resort_autonomy_after_scheduling_gather() -> None:
    """The turn that schedules a mandatory gather does not call Orchestrator."""
    state = new_game(1)
    state.day = 4
    state.phase = Phase.AFTERNOON

    def fail_orchestrator(_state):
        raise AssertionError("resort autonomy should pause while gather is pending")

    result = run_turn(
        state,
        PlayerAction(kind=ActionKind.AMBIENT, target_id="ambient_wait"),
        SeededRng(1),
        replace(MOCK_AGENTS, resort_orchestrator=fail_orchestrator),
    )

    assert result.state.pending_gather is not None
    assert result.agent_commits.resort_update is None


def test_join_gather_resolves_flush_of_hearts_arrival() -> None:
    """JOIN_GATHER moves the resort to the flame_deck and then resolves the event."""
    state = new_game(1)
    state.day = 4
    state.phase = Phase.AFTERNOON
    run_turn(
        state,
        PlayerAction(kind=ActionKind.AMBIENT, target_id="ambient_wait"),
        SeededRng(1),
        MOCK_AGENTS,
    )

    result = run_turn(state, PlayerAction(kind=ActionKind.JOIN_GATHER), SeededRng(2), MOCK_AGENTS)

    assert any(event.kind == "flush_of_hearts_arrival" for event in result.ceremony_events)
    assert result.state.pending_gather is None
    assert result.state.flush_of_hearts_state is not None
    assert result.event_narration is not None


def test_join_gather_closes_active_and_background_conversations() -> None:
    """Mandatory gathers clear conversations before event narration."""
    state = new_game(1)
    rng = SeededRng(1)
    run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION, target_id="chloe", intent_id="friendly_chat_resort"
        ),
        rng,
        FOLLOW_UP_AGENTS,
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
        event_id="pairing_day_3",
        gather_location=Location.FLAME_DECK,
        fires_on_turn=state.turn_index + 1,
    )
    state.day = 3
    state.phase = Phase.EVENING

    result = run_turn(state, PlayerAction(kind=ActionKind.JOIN_GATHER), rng, MOCK_AGENTS)

    assert result.state.active_conversation is None
    assert result.state.npc_conversations == []
    assert all(
        heartbreaker.location_id is not Location.TERRACE
        for heartbreaker in result.state.heartbreakers
    )
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
            recap_disposition=RecapDisposition.WHILE_BUSY,
        ),
    )

    result = run_turn(
        state,
        PlayerAction(kind=ActionKind.AMBIENT, target_id="ambient_wait"),
        SeededRng(1),
        MOCK_AGENTS,
    )

    assert result.state.day == 2
    assert result.state.daily_recaps
    assert (
        result.state.daily_recaps[0].items[0].content == "Maya and Liam had a sharp terrace moment."
    )


def test_apply_action_does_not_bump_turn_index() -> None:
    """Turn bookkeeping only happens inside run_turn."""
    state = new_game(1)

    apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
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
            intent_id="friendly_chat_resort",
        ),
        rng,
        FOLLOW_UP_AGENTS,
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
        replace(FOLLOW_UP_AGENTS, conversation_curator=curator),
    )

    assert result.exchange is not None
    assert result.state.active_conversation is None
    assert result.mechanical_result.relationship_deltas["chloe"].trust == 1
    assert calls == 1
    assert result.curator_batches
    assert result.curator_batches[0].kind == "player"


def test_walk_away_closes_conversation_and_applies_affection_penalty() -> None:
    """Top-level END_CONVERSATION is a curt walk-away, not a graceful wheel exit."""
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
        FOLLOW_UP_AGENTS,
    )
    affection_before = state.heartbreakers[0].relationship.affection
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
        replace(MOCK_AGENTS, conversation_curator=curator),
    )

    assert result.exchange is None
    assert result.state.active_conversation is None
    assert state.heartbreakers[0].relationship.affection == affection_before - 1
    assert result.mechanical_result.relationship_deltas["chloe"].affection == -1
    assert calls == 1
    assert result.curator_batches
    assert result.curator_batches[0].kind == "player"


def test_pending_gather_does_not_call_event_narrator() -> None:
    state = new_game(1)

    def narrator(*_args):
        raise AssertionError("pending gathers use deterministic UI copy")

    narration = _narrated_events(
        state,
        [CeremonyEvent(kind="gather_scheduled", message="Join the gather.")],
        narrator,
    )

    assert narration is None
