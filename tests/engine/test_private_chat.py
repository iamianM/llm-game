"""Tests for private-chat mechanics."""

from __future__ import annotations

from dataclasses import replace

from src.game.agents.contextual_options import mock_follow_up_menu
from src.game.agents.turn_agents import mock_turn_agents
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.phases import advance_phase
from src.game.engine.private_chat import (
    attempt_private_chat,
    private_chat_chance,
    target_in_active_conversation,
)
from src.game.engine.turn import run_turn
from src.game.state.models import Location, NPCNPCConversation, new_game
from src.game.state.rng import SeededRng

FOLLOW_UP_AGENTS = replace(
    mock_turn_agents(), contextual_options=lambda *_args: mock_follow_up_menu()
)


def test_private_chat_chance_higher_with_more_spark() -> None:
    """Spark increases private-chat chance at the same relationship state."""
    low = _state_with_busy_chloe()
    high = _state_with_busy_chloe()
    low.player.stats.spark = 3
    high.player.stats.spark = 9

    assert private_chat_chance(high, "chloe") > private_chat_chance(low, "chloe")


def test_private_chat_chance_lower_when_target_chemistry_strong() -> None:
    """Strong chemistry on the target makes inviting them away harder."""
    state = _state_with_busy_chloe()
    baseline = private_chat_chance(state, "chloe")

    state.heartbreakers[0].relationship.chemistry = 90

    assert private_chat_chance(state, "chloe") < baseline


def test_private_chat_chance_privacy_modifier_applied() -> None:
    """Private locations make private chats easier than busy spaces."""
    bedroom = _state_with_busy_chloe(location=Location.BEDROOM)
    pool = _state_with_busy_chloe(location=Location.POOL)
    kitchen = _state_with_busy_chloe(location=Location.KITCHEN)

    assert (
        private_chat_chance(bedroom, "chloe")
        > private_chat_chance(pool, "chloe")
        > private_chat_chance(kitchen, "chloe")
    )


def test_private_chat_chance_supports_flush_locations() -> None:
    """Flush of Hearts locations use the same privacy bands as the main resort."""
    pool = _state_with_busy_chloe(location=Location.FLUSH_POOL)
    terrace = _state_with_busy_chloe(location=Location.FLUSH_TERRACE)
    kitchen = _state_with_busy_chloe(location=Location.FLUSH_KITCHEN)

    assert (
        private_chat_chance(terrace, "chloe")
        > private_chat_chance(pool, "chloe")
        > private_chat_chance(kitchen, "chloe")
    )


def test_private_chat_chance_supports_flame_deck() -> None:
    """Mandatory gather location has a crowded-space modifier, not a KeyError."""
    state = _state_with_busy_chloe(location=Location.FLAME_DECK)

    assert private_chat_chance(state, "chloe") >= 10


def test_private_chat_chance_drops_with_repeated_attempts() -> None:
    state = _state_with_busy_chloe()
    baseline = private_chat_chance(state, "chloe")

    state.player.private_chat_attempts_this_phase["chloe"] = 1

    assert private_chat_chance(state, "chloe") == baseline - 15


def test_three_failed_private_chats_clamped_near_minimum() -> None:
    state = _state_with_busy_chloe(location=Location.KITCHEN)
    state.player.stats.spark = 3
    state.heartbreakers[0].relationship.chemistry = 100
    state.player.private_chat_attempts_this_phase["chloe"] = 3

    assert private_chat_chance(state, "chloe") == 10


def test_private_chat_chance_clamped_to_10_90() -> None:
    """Extreme inputs stay inside the private chat chance clamp."""
    low = _state_with_busy_chloe(location=Location.KITCHEN)
    low.player.stats.spark = 3
    low.heartbreakers[0].relationship.affection = 0
    low.heartbreakers[0].relationship.chemistry = 100
    high = _state_with_busy_chloe(location=Location.BEDROOM)
    high.player.stats.spark = 9
    high.heartbreakers[0].relationship.affection = 100
    high.heartbreakers[0].relationship.chemistry = 0

    assert private_chat_chance(low, "chloe") == 24
    assert private_chat_chance(high, "chloe") == 90


def test_target_in_active_conversation_returns_correct_conv() -> None:
    """The active conversation lookup returns the target's current NPC chat."""
    state = _state_with_busy_chloe()

    assert target_in_active_conversation(state, "chloe") == state.npc_conversations[0]
    assert target_in_active_conversation(state, "liam") is None


def test_private_chat_skipped_when_target_alone_no_roll_needed() -> None:
    """START_CONVERSATION on an unblocked target starts normally without PrivateChatAttempt."""
    state = new_game(1)

    turn = run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        SeededRng(1),
        FOLLOW_UP_AGENTS,
    )

    assert turn.mechanical_result.private_chat_attempt is None
    assert turn.state.active_conversation is not None


def test_start_conversation_with_private_chat_success_opens_new_convo() -> None:
    """A successful private chat closes the old NPC chat and opens the player's chat."""
    state = _state_with_busy_chloe(location=Location.BEDROOM)
    state.player.stats.spark = 9
    state.heartbreakers[0].relationship.affection = 100

    turn = run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        SeededRng(1),
        FOLLOW_UP_AGENTS,
    )

    assert turn.mechanical_result.private_chat_attempt is not None
    assert turn.mechanical_result.private_chat_attempt.success is True
    assert state.active_conversation is not None
    assert state.active_conversation.target_id == "chloe"
    assert state.npc_conversations == []
    assert turn.curator_batches
    assert [closure.model_dump(mode="json") for closure in turn.conversation_closures] == [
        {
            "conversation_id": "npcconv_busy",
            "participant_ids": ["chloe", "maya"],
            "reason": "private_chat_success",
        }
    ]


def test_start_conversation_with_private_chat_failure_does_not_open() -> None:
    """A missed private chat produces a deflection and leaves the player without a conversation."""
    state = _state_with_busy_chloe(location=Location.KITCHEN)
    state.player.stats.spark = 3
    state.heartbreakers[0].relationship.chemistry = 100
    affection_before = state.heartbreakers[0].relationship.affection

    turn = run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        SeededRng(3),
        FOLLOW_UP_AGENTS,
    )

    assert turn.mechanical_result.private_chat_attempt is not None
    assert turn.mechanical_result.private_chat_attempt.success is False
    assert turn.exchange is not None
    assert state.active_conversation is None
    assert state.npc_conversations
    assert state.heartbreakers[0].relationship.affection == affection_before - 1
    assert state.player.private_chat_attempts_this_phase["chloe"] == 1


def test_private_chat_attempts_reset_on_phase_advance() -> None:
    state = _state_with_busy_chloe()
    state.player.private_chat_attempts_this_phase["chloe"] = 2

    advance_phase(state)

    assert state.player.private_chat_attempts_this_phase == {}


def test_repeated_private_chat_creates_clingy_memory() -> None:
    state = _state_with_busy_chloe(location=Location.KITCHEN)
    state.player.stats.spark = 3
    state.heartbreakers[0].relationship.chemistry = 100

    attempt_private_chat(state, "chloe", SeededRng(3))
    attempt_private_chat(state, "chloe", SeededRng(3))

    chloe = next(heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == "chloe")
    assert any("player_kept_requesting_private_chats" in memory.tags for memory in chloe.memories)


def test_private_chat_failure_bystanders_get_witness_memory() -> None:
    """Bystanders at the location remember a rejected private chat."""
    state = _state_with_busy_chloe(location=Location.KITCHEN)
    state.player.stats.spark = 3
    state.heartbreakers[0].relationship.chemistry = 100

    run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        SeededRng(3),
        FOLLOW_UP_AGENTS,
    )

    maya = next(heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == "maya")
    assert any("saw_private_chat_rejected" in memory.tags for memory in maya.memories)


def test_attempt_private_chat_records_blocked_conversation_id() -> None:
    """PrivateChatAttempt records the blocked conversation for trace review."""
    state = _state_with_busy_chloe()

    attempt = attempt_private_chat(state, "chloe", SeededRng(1))

    assert attempt.blocked_conversation_id == "npcconv_busy"
    assert attempt.target_id == "chloe"


def _state_with_busy_chloe(*, location: Location = Location.POOL):
    state = new_game(1)
    state.location_id = location
    state.heartbreakers[0].location_id = location
    state.heartbreakers[1].location_id = location
    state.npc_conversations.append(
        NPCNPCConversation(
            id="npcconv_busy",
            participants=["chloe", "maya"],
            location_id=location,
            topic="private first impressions",
            started_on_turn=0,
        )
    )
    return state
