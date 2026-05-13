"""Tests for pull-for-chat mechanics."""

from __future__ import annotations

from src.game.agents.contextual_options import mock_follow_up_menu
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.phases import advance_phase
from src.game.engine.pull import attempt_pull, pull_chance, target_in_active_conversation
from src.game.engine.turn import run_turn
from src.game.state.models import Location, NPCNPCConversation, new_game
from src.game.state.rng import SeededRng


def test_pull_chance_higher_with_more_graft() -> None:
    """Graft increases pull chance at the same relationship state."""
    low = _state_with_busy_chloe()
    high = _state_with_busy_chloe()
    low.player.stats.graft = 3
    high.player.stats.graft = 9

    assert pull_chance(high, "chloe") > pull_chance(low, "chloe")


def test_pull_chance_lower_when_target_chemistry_strong() -> None:
    """Strong chemistry on the target makes pulling them away harder."""
    state = _state_with_busy_chloe()
    baseline = pull_chance(state, "chloe")

    state.islanders[0].relationship.chemistry = 90

    assert pull_chance(state, "chloe") < baseline


def test_pull_chance_privacy_modifier_applied() -> None:
    """Private locations make pulls easier than busy spaces."""
    bedroom = _state_with_busy_chloe(location=Location.BEDROOM)
    pool = _state_with_busy_chloe(location=Location.POOL)
    kitchen = _state_with_busy_chloe(location=Location.KITCHEN)

    assert pull_chance(bedroom, "chloe") > pull_chance(pool, "chloe") > pull_chance(kitchen, "chloe")


def test_pull_chance_supports_casa_locations() -> None:
    """Casa Amor locations use the same privacy bands as the main villa."""
    pool = _state_with_busy_chloe(location=Location.CASA_POOL)
    terrace = _state_with_busy_chloe(location=Location.CASA_TERRACE)
    kitchen = _state_with_busy_chloe(location=Location.CASA_KITCHEN)

    assert pull_chance(terrace, "chloe") > pull_chance(pool, "chloe") > pull_chance(kitchen, "chloe")


def test_pull_chance_drops_with_repeated_attempts() -> None:
    state = _state_with_busy_chloe()
    baseline = pull_chance(state, "chloe")

    state.player.pull_attempts_this_phase["chloe"] = 1

    assert pull_chance(state, "chloe") == baseline - 15


def test_three_failed_pulls_clamped_near_minimum() -> None:
    state = _state_with_busy_chloe(location=Location.KITCHEN)
    state.player.stats.graft = 3
    state.islanders[0].relationship.chemistry = 100
    state.player.pull_attempts_this_phase["chloe"] = 3

    assert pull_chance(state, "chloe") == 10


def test_pull_chance_clamped_to_10_90() -> None:
    """Extreme inputs stay inside the pull chance clamp."""
    low = _state_with_busy_chloe(location=Location.KITCHEN)
    low.player.stats.graft = 3
    low.islanders[0].relationship.affection = 0
    low.islanders[0].relationship.chemistry = 100
    high = _state_with_busy_chloe(location=Location.BEDROOM)
    high.player.stats.graft = 9
    high.islanders[0].relationship.affection = 100
    high.islanders[0].relationship.chemistry = 0

    assert pull_chance(low, "chloe") == 24
    assert pull_chance(high, "chloe") == 90


def test_target_in_active_conversation_returns_correct_conv() -> None:
    """The active conversation lookup returns the target's current NPC chat."""
    state = _state_with_busy_chloe()

    assert target_in_active_conversation(state, "chloe") == state.npc_conversations[0]
    assert target_in_active_conversation(state, "liam") is None


def test_pull_skipped_when_target_alone_no_roll_needed() -> None:
    """START_CONVERSATION on an unblocked target starts normally without PullAttempt."""
    state = new_game(1)

    turn = run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(1),
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )

    assert turn.mechanical_result.pull_attempt is None
    assert turn.state.active_conversation is not None


def test_start_conversation_with_pull_success_opens_new_convo() -> None:
    """A successful pull closes the old NPC chat and opens the player's chat."""
    state = _state_with_busy_chloe(location=Location.BEDROOM)
    state.player.stats.graft = 9
    state.islanders[0].relationship.affection = 100

    turn = run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(1),
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )

    assert turn.mechanical_result.pull_attempt is not None
    assert turn.mechanical_result.pull_attempt.success is True
    assert state.active_conversation is not None
    assert state.active_conversation.target_id == "chloe"
    assert state.npc_conversations == []
    assert turn.curator_batches


def test_start_conversation_with_pull_failure_does_not_open() -> None:
    """A missed pull produces a deflection and leaves the player without a conversation."""
    state = _state_with_busy_chloe(location=Location.KITCHEN)
    state.player.stats.graft = 3
    state.islanders[0].relationship.chemistry = 100
    affection_before = state.islanders[0].relationship.affection

    turn = run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(3),
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )

    assert turn.mechanical_result.pull_attempt is not None
    assert turn.mechanical_result.pull_attempt.success is False
    assert turn.exchange is not None
    assert state.active_conversation is None
    assert state.npc_conversations
    assert state.islanders[0].relationship.affection == affection_before - 1
    assert state.player.pull_attempts_this_phase["chloe"] == 1


def test_pull_attempts_reset_on_phase_advance() -> None:
    state = _state_with_busy_chloe()
    state.player.pull_attempts_this_phase["chloe"] = 2

    advance_phase(state)

    assert state.player.pull_attempts_this_phase == {}


def test_repeated_pull_creates_clingy_memory() -> None:
    state = _state_with_busy_chloe(location=Location.KITCHEN)
    state.player.stats.graft = 3
    state.islanders[0].relationship.chemistry = 100

    attempt_pull(state, "chloe", SeededRng(3))
    attempt_pull(state, "chloe", SeededRng(3))

    chloe = next(islander for islander in state.islanders if islander.id == "chloe")
    assert any("player_kept_pulling" in memory.tags for memory in chloe.memories)


def test_pull_failure_bystanders_get_witness_memory() -> None:
    """Bystanders at the location remember a rejected pull."""
    state = _state_with_busy_chloe(location=Location.KITCHEN)
    state.player.stats.graft = 3
    state.islanders[0].relationship.chemistry = 100

    run_turn(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(3),
        contextual_options=lambda *_args: mock_follow_up_menu(),
    )

    maya = next(islander for islander in state.islanders if islander.id == "maya")
    assert any("saw_pull_rejected" in memory.tags for memory in maya.memories)


def test_attempt_pull_records_blocked_conversation_id() -> None:
    """PullAttempt records the blocked conversation for trace review."""
    state = _state_with_busy_chloe()

    attempt = attempt_pull(state, "chloe", SeededRng(1))

    assert attempt.blocked_conversation_id == "npcconv_busy"
    assert attempt.target_id == "chloe"


def _state_with_busy_chloe(*, location: Location = Location.POOL):
    state = new_game(1)
    state.location_id = location
    state.islanders[0].location_id = location
    state.islanders[1].location_id = location
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
