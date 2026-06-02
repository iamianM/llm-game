"""Tests for Resort Orchestrator commit validation and application."""

from __future__ import annotations

import pytest

from src.game.agents.resort_orchestrator import (
    ContinueConversation,
    EndConversation,
    NewConversation,
    NPCMovement,
    ResortUpdate,
)
from src.game.agents.runtime import AgentGenerationError, AgentValidationError
from src.game.engine.resort import (
    apply_resort_update,
    normalize_resort_update,
    validate_resort_update,
)
from src.game.engine.turn_autonomy import apply_resort_turn
from src.game.state.models import (
    GameState,
    Location,
    NPCNPCConversation,
    PendingGather,
    new_game,
)
from src.game.state.rng import SeededRng


def test_resort_update_rejects_eliminated_npc() -> None:
    """The Orchestrator cannot use eliminated heartbreakers."""
    state = new_game(1)
    state.heartbreakers[0].eliminated = True
    update = ResortUpdate(
        npc_movements=[NPCMovement(npc_id="chloe", target_location=Location.POOL, reason="drift")]
    )

    with pytest.raises(ValueError, match="eliminated"):
        validate_resort_update(state, update)


def test_resort_update_rejects_player_in_npc_conv() -> None:
    """NPC-NPC conversations never include the player."""
    state = new_game(1)
    update = ResortUpdate(
        conversation_starts=[
            NewConversation(participants=["player", "chloe"], location=Location.POOL, topic="bad")
        ]
    )

    with pytest.raises(ValueError, match="player"):
        validate_resort_update(state, update)


def test_resort_update_rejects_start_at_wrong_location() -> None:
    """Starts require both NPCs to be co-located after movements apply."""
    state = new_game(1)
    update = ResortUpdate(
        conversation_starts=[
            NewConversation(
                participants=["chloe", "maya"],
                location=Location.POOL,
                topic="comparing notes",
            )
        ]
    )

    with pytest.raises(ValueError, match="not at location"):
        validate_resort_update(state, update)


def test_resort_update_rejects_end_and_continue_same_conv() -> None:
    """A conversation cannot both continue and end in one update."""
    state = new_game(1)
    state.npc_conversations.append(_npc_conversation())
    update = ResortUpdate(
        conversation_continues=[ContinueConversation(conversation_id="npcconv_test")],
        conversation_ends=[EndConversation(conversation_id="npcconv_test", reason="natural_end")],
    )

    with pytest.raises(ValueError, match="end and continue"):
        validate_resort_update(state, update)


def test_resort_update_rejects_movement_during_pending_gather() -> None:
    """Autonomy pauses while mandatory gather actions are waiting."""
    state = new_game(1)
    state.pending_gather = PendingGather(
        kind="ceremony",
        event_id="pairing_day_3",
        gather_location=Location.FLAME_DECK,
        fires_on_turn=1,
    )
    update = ResortUpdate(
        npc_movements=[NPCMovement(npc_id="chloe", target_location=Location.KITCHEN, reason="drift")]
    )

    with pytest.raises(ValueError, match="gather is pending"):
        validate_resort_update(state, update)


def test_apply_movements_updates_locations() -> None:
    """Validated movement commits mutate NPC location."""
    state = new_game(1)
    update = ResortUpdate(
        npc_movements=[NPCMovement(npc_id="maya", target_location=Location.POOL, reason="joining")]
    )

    apply_resort_update(state, update, SeededRng(1))

    assert state.heartbreakers[1].location_id is Location.POOL


def test_moving_conversation_participant_implies_conversation_end() -> None:
    state = new_game(1)
    conversation = _npc_conversation()
    state.npc_conversations.append(conversation)
    update = ResortUpdate(
        npc_movements=[NPCMovement(npc_id="chloe", target_location=Location.KITCHEN, reason="drift")],
        conversation_continues=[ContinueConversation(conversation_id=conversation.id)],
    )

    normalized = normalize_resort_update(state, update)

    validate_resort_update(state, normalized)
    assert normalized.conversation_continues == []
    assert normalized.conversation_ends[0].conversation_id == conversation.id
    assert normalized.conversation_ends[0].reason == "participant_moved"


def test_stale_conversation_location_implies_conversation_end() -> None:
    state = new_game(1)
    conversation = _npc_conversation()
    state.npc_conversations.append(conversation)
    state.heartbreakers[0].location_id = Location.KITCHEN

    normalized = normalize_resort_update(state, ResortUpdate())

    validate_resort_update(state, normalized)
    assert normalized.conversation_ends[0].conversation_id == conversation.id


def test_npc_conversation_close_invokes_curator() -> None:
    """Closing an NPC-NPC conversation creates memories for participants."""
    state = new_game(1)
    conversation = _npc_conversation()
    state.npc_conversations.append(conversation)
    update = ResortUpdate(
        conversation_ends=[EndConversation(conversation_id=conversation.id, reason="natural_end")]
    )

    changes = apply_resort_update(state, update, SeededRng(1))

    assert changes.curator_batches
    assert changes.curator_batches[0].kind == "background"
    assert state.npc_conversations == []
    assert state.heartbreakers[0].memories
    assert state.heartbreakers[1].memories


def test_npc_conversation_close_survives_curator_raise() -> None:
    """The async curator exhausting its retries and raising during the resort turn
    must not dead-screen the player — closing an NPC-NPC conversation degrades to the
    deterministic mock curator and still records participant memories."""
    state = new_game(1)
    conversation = _npc_conversation()
    state.npc_conversations.append(conversation)
    update = ResortUpdate(
        conversation_ends=[EndConversation(conversation_id=conversation.id, reason="natural_end")]
    )

    def boom(*_args, **_kwargs):
        raise AgentValidationError("curator exhausted retries")

    changes = apply_resort_update(state, update, SeededRng(1), conversation_curator=boom)

    assert changes.curator_batches
    assert changes.curator_batches[0].kind == "background"
    assert state.npc_conversations == []
    assert state.heartbreakers[0].memories
    assert state.heartbreakers[1].memories


def test_conversation_start_creates_background_exchange() -> None:
    """Starting a background conversation creates persistent state and an exchange."""
    state = new_game(1)
    state.heartbreakers[1].location_id = Location.POOL
    update = ResortUpdate(
        conversation_starts=[
            NewConversation(
                participants=["chloe", "maya"],
                location=Location.POOL,
                topic="gossip about the morning",
            )
        ]
    )

    changes = apply_resort_update(state, update, SeededRng(1))

    assert len(state.npc_conversations) == 1
    assert len(state.npc_conversations[0].exchanges) == 1
    assert len(changes.background_dialogues) == 1


def test_conversation_start_survives_background_dialogue_raise() -> None:
    """Background NPC-NPC chatter is pure ambient flavor; the dialogue agent giving
    up and raising must not dead-screen the player's turn — starting the conversation
    degrades to the deterministic mock exchange and still records it."""
    state = new_game(1)
    state.heartbreakers[1].location_id = Location.POOL
    update = ResortUpdate(
        conversation_starts=[
            NewConversation(
                participants=["chloe", "maya"],
                location=Location.POOL,
                topic="gossip about the morning",
            )
        ]
    )

    def boom(*_args, **_kwargs):
        raise AgentGenerationError("background dialogue exhausted retries")

    changes = apply_resort_update(state, update, SeededRng(1), background_dialogue=boom)

    assert len(state.npc_conversations) == 1
    assert len(state.npc_conversations[0].exchanges) == 1
    assert len(changes.background_dialogues) == 1


def test_normalize_resolves_wrong_case_movement() -> None:
    """A wrong-case id (the live 'Jordan' vs 'jordan' slip) is repaired
    before validation instead of dead-screening the turn."""
    state = new_game(1)
    update = ResortUpdate(
        npc_movements=[NPCMovement(npc_id="Jordan", target_location=Location.KITCHEN, reason="drift")]
    )

    normalized = normalize_resort_update(state, update)

    assert normalized.npc_movements[0].npc_id == "jordan"
    validate_resort_update(state, normalized)


def test_normalize_resolves_display_name_in_conversation_start() -> None:
    """Conversation-start participants given by display name / wrong case (the exact
    live crash site) resolve to canonical ids so the start validates."""
    state = new_game(1)
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id in {"jordan", "sophie"}:
            heartbreaker.location_id = Location.POOL
    update = ResortUpdate(
        conversation_starts=[
            NewConversation(
                participants=["Jordan", "Sophie"],
                location=Location.POOL,
                topic="comparing notes",
            )
        ]
    )

    normalized = normalize_resort_update(state, update)

    assert normalized.conversation_starts[0].participants == ["jordan", "sophie"]
    validate_resort_update(state, normalized)


def test_normalize_leaves_unknown_npc_untouched() -> None:
    """A genuinely unknown token is left alone so validation rejects it clearly."""
    state = new_game(1)
    update = ResortUpdate(
        npc_movements=[NPCMovement(npc_id="ghost", target_location=Location.KITCHEN, reason="drift")]
    )

    normalized = normalize_resort_update(state, update)

    assert normalized.npc_movements[0].npc_id == "ghost"
    with pytest.raises(ValueError, match="unknown or eliminated"):
        validate_resort_update(state, normalized)


def test_apply_resort_turn_survives_orchestrator_raise() -> None:
    """The ambient orchestrator giving up (its live 3-retry exhaustion) must not
    dead-screen the turn — the resort simply holds still for one turn."""
    state = new_game(1)
    before = {heartbreaker.id: heartbreaker.location_id for heartbreaker in state.heartbreakers}

    def boom(_state: GameState) -> ResortUpdate:
        raise AgentValidationError("unknown or eliminated NPC in ResortUpdate: jordan")

    resort_update, changes, arrival_rolls = apply_resort_turn(
        state, SeededRng(1), boom, background_dialogue=None, conversation_curator=None
    )

    assert resort_update == ResortUpdate()
    assert changes.resort_update == ResortUpdate()
    assert arrival_rolls == []
    # No ambient mutation leaked through on the failure path.
    assert {heartbreaker.id: heartbreaker.location_id for heartbreaker in state.heartbreakers} == before


def test_apply_resort_turn_drops_unrepairable_update() -> None:
    """An invalid update that near-miss id repair cannot fix is dropped to empty
    rather than propagating the validation error up through the turn."""
    state = new_game(1)
    before = {heartbreaker.id: heartbreaker.location_id for heartbreaker in state.heartbreakers}

    def ghost_mover(_state: GameState) -> ResortUpdate:
        return ResortUpdate(
            npc_movements=[
                NPCMovement(npc_id="ghost", target_location=Location.KITCHEN, reason="drift")
            ]
        )

    resort_update, _changes, _rolls = apply_resort_turn(
        state, SeededRng(1), ghost_mover, background_dialogue=None, conversation_curator=None
    )

    assert resort_update == ResortUpdate()
    assert {heartbreaker.id: heartbreaker.location_id for heartbreaker in state.heartbreakers} == before


def test_apply_resort_turn_preserves_pending_summon_when_llm_update_invalid() -> None:
    """A queued summon is internally derived and valid; it should still fire even
    when the LLM's own movement/chatter for the turn is unusable and dropped."""
    from src.game.state.autonomy import PendingNPCSummon

    state = new_game(1)
    # Player is mid-conversation with maya; a summon is queued to call her away.
    from src.game.engine.conversation import start_conversation

    maya = next(heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == "maya")
    maya.location_id = state.location_id
    start_conversation(state, "maya", state.turn_index)
    state.pending_npc_summon = PendingNPCSummon(
        npc_id="maya",
        from_conversation_id="player_active",
        reason="chemistry_partner_arrived",
        target_location=Location.POOL.value,
    )

    def ghost_mover(_state: GameState) -> ResortUpdate:
        return ResortUpdate(
            npc_movements=[
                NPCMovement(npc_id="ghost", target_location=Location.KITCHEN, reason="drift")
            ]
        )

    resort_update, _changes, _rolls = apply_resort_turn(
        state, SeededRng(1), ghost_mover, background_dialogue=None, conversation_curator=None
    )

    # The bad LLM movement was dropped, but the guarded summon survived the merge.
    assert resort_update.npc_movements == []
    assert [summon.npc_id for summon in resort_update.npc_summoned_elsewhere] == ["maya"]
    assert state.pending_npc_summon is None


def test_apply_resort_turn_drops_summon_that_conflicts_with_movement() -> None:
    """If the orchestrator validly moves the active partner the same turn a summon
    for that partner is queued, the combined update is invalid ("cannot summon and
    move the same NPC"). Keep the valid movement and drop the summon — never crash."""
    from src.game.engine.conversation import start_conversation
    from src.game.state.autonomy import PendingNPCSummon

    state = new_game(1)
    maya = next(heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == "maya")
    maya.location_id = state.location_id
    start_conversation(state, "maya", state.turn_index)
    state.pending_npc_summon = PendingNPCSummon(
        npc_id="maya",
        from_conversation_id="player_active",
        reason="chemistry_partner_arrived",
        target_location=Location.POOL.value,
    )

    def move_maya(_state: GameState) -> ResortUpdate:
        return ResortUpdate(
            npc_movements=[
                NPCMovement(npc_id="maya", target_location=Location.KITCHEN, reason="drift")
            ]
        )

    resort_update, _changes, _rolls = apply_resort_turn(
        state, SeededRng(1), move_maya, background_dialogue=None, conversation_curator=None
    )

    # The valid movement survived; the conflicting summon was dropped, not crashed.
    assert resort_update.npc_summoned_elsewhere == []
    assert [m.npc_id for m in resort_update.npc_movements] == ["maya"]
    assert maya.location_id is Location.KITCHEN


def _npc_conversation() -> NPCNPCConversation:
    return NPCNPCConversation(
        id="npcconv_test",
        participants=["chloe", "maya"],
        location_id=Location.POOL,
        topic="a private chat",
        started_on_turn=1,
    )
