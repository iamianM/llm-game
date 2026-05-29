"""Tests for Villa Orchestrator commit validation and application."""

from __future__ import annotations

import pytest

from src.game.agents.runtime import AgentGenerationError, AgentValidationError
from src.game.agents.villa_orchestrator import (
    ContinueConversation,
    EndConversation,
    NewConversation,
    NPCMovement,
    VillaUpdate,
)
from src.game.engine.turn_autonomy import apply_villa_turn
from src.game.engine.villa import apply_villa_update, normalize_villa_update, validate_villa_update
from src.game.state.models import (
    GameState,
    Location,
    NPCNPCConversation,
    PendingGather,
    new_game,
)
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


def test_npc_conversation_close_survives_curator_raise() -> None:
    """The async curator exhausting its retries and raising during the villa turn
    must not dead-screen the player — closing an NPC-NPC conversation degrades to the
    deterministic mock curator and still records participant memories."""
    state = new_game(1)
    conversation = _npc_conversation()
    state.npc_conversations.append(conversation)
    update = VillaUpdate(
        conversation_ends=[EndConversation(conversation_id=conversation.id, reason="natural_end")]
    )

    def boom(*_args, **_kwargs):
        raise AgentValidationError("curator exhausted retries")

    changes = apply_villa_update(state, update, SeededRng(1), conversation_curator=boom)

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


def test_conversation_start_survives_background_dialogue_raise() -> None:
    """Background NPC-NPC chatter is pure ambient flavor; the dialogue agent giving
    up and raising must not dead-screen the player's turn — starting the conversation
    degrades to the deterministic mock exchange and still records it."""
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

    def boom(*_args, **_kwargs):
        raise AgentGenerationError("background dialogue exhausted retries")

    changes = apply_villa_update(state, update, SeededRng(1), background_dialogue=boom)

    assert len(state.npc_conversations) == 1
    assert len(state.npc_conversations[0].exchanges) == 1
    assert len(changes.background_dialogues) == 1


def test_normalize_resolves_wrong_case_movement() -> None:
    """A wrong-case id (the live 'Jordan' vs 'jordan' slip) is repaired
    before validation instead of dead-screening the turn."""
    state = new_game(1)
    update = VillaUpdate(
        npc_movements=[NPCMovement(npc_id="Jordan", target_location=Location.KITCHEN, reason="drift")]
    )

    normalized = normalize_villa_update(state, update)

    assert normalized.npc_movements[0].npc_id == "jordan"
    validate_villa_update(state, normalized)


def test_normalize_resolves_display_name_in_conversation_start() -> None:
    """Conversation-start participants given by display name / wrong case (the exact
    live crash site) resolve to canonical ids so the start validates."""
    state = new_game(1)
    for islander in state.islanders:
        if islander.id in {"jordan", "sophie"}:
            islander.location_id = Location.POOL
    update = VillaUpdate(
        conversation_starts=[
            NewConversation(
                participants=["Jordan", "Sophie"],
                location=Location.POOL,
                topic="comparing notes",
            )
        ]
    )

    normalized = normalize_villa_update(state, update)

    assert normalized.conversation_starts[0].participants == ["jordan", "sophie"]
    validate_villa_update(state, normalized)


def test_normalize_leaves_unknown_npc_untouched() -> None:
    """A genuinely unknown token is left alone so validation rejects it clearly."""
    state = new_game(1)
    update = VillaUpdate(
        npc_movements=[NPCMovement(npc_id="ghost", target_location=Location.KITCHEN, reason="drift")]
    )

    normalized = normalize_villa_update(state, update)

    assert normalized.npc_movements[0].npc_id == "ghost"
    with pytest.raises(ValueError, match="unknown or eliminated"):
        validate_villa_update(state, normalized)


def test_apply_villa_turn_survives_orchestrator_raise() -> None:
    """The ambient orchestrator giving up (its live 3-retry exhaustion) must not
    dead-screen the turn — the villa simply holds still for one turn."""
    state = new_game(1)
    before = {islander.id: islander.location_id for islander in state.islanders}

    def boom(_state: GameState) -> VillaUpdate:
        raise AgentValidationError("unknown or eliminated NPC in VillaUpdate: jordan")

    villa_update, changes, arrival_rolls = apply_villa_turn(
        state, SeededRng(1), boom, background_dialogue=None, conversation_curator=None
    )

    assert villa_update == VillaUpdate()
    assert changes.villa_update == VillaUpdate()
    assert arrival_rolls == []
    # No ambient mutation leaked through on the failure path.
    assert {islander.id: islander.location_id for islander in state.islanders} == before


def test_apply_villa_turn_drops_unrepairable_update() -> None:
    """An invalid update that near-miss id repair cannot fix is dropped to empty
    rather than propagating the validation error up through the turn."""
    state = new_game(1)
    before = {islander.id: islander.location_id for islander in state.islanders}

    def ghost_mover(_state: GameState) -> VillaUpdate:
        return VillaUpdate(
            npc_movements=[
                NPCMovement(npc_id="ghost", target_location=Location.KITCHEN, reason="drift")
            ]
        )

    villa_update, _changes, _rolls = apply_villa_turn(
        state, SeededRng(1), ghost_mover, background_dialogue=None, conversation_curator=None
    )

    assert villa_update == VillaUpdate()
    assert {islander.id: islander.location_id for islander in state.islanders} == before


def test_apply_villa_turn_preserves_pending_summon_when_llm_update_invalid() -> None:
    """A queued summon is internally derived and valid; it should still fire even
    when the LLM's own movement/chatter for the turn is unusable and dropped."""
    from src.game.state.autonomy import PendingNPCSummon

    state = new_game(1)
    # Player is mid-conversation with maya; a summon is queued to pull her away.
    from src.game.engine.conversation import start_conversation

    maya = next(islander for islander in state.islanders if islander.id == "maya")
    maya.location_id = state.location_id
    start_conversation(state, "maya", state.turn_index)
    state.pending_npc_summon = PendingNPCSummon(
        npc_id="maya",
        from_conversation_id="player_active",
        reason="chemistry_partner_arrived",
        target_location=Location.POOL.value,
    )

    def ghost_mover(_state: GameState) -> VillaUpdate:
        return VillaUpdate(
            npc_movements=[
                NPCMovement(npc_id="ghost", target_location=Location.KITCHEN, reason="drift")
            ]
        )

    villa_update, _changes, _rolls = apply_villa_turn(
        state, SeededRng(1), ghost_mover, background_dialogue=None, conversation_curator=None
    )

    # The bad LLM movement was dropped, but the guarded summon survived the merge.
    assert villa_update.npc_movements == []
    assert [summon.npc_id for summon in villa_update.npc_summoned_elsewhere] == ["maya"]
    assert state.pending_npc_summon is None


def test_apply_villa_turn_drops_summon_that_conflicts_with_movement() -> None:
    """If the orchestrator validly moves the active partner the same turn a summon
    for that partner is queued, the combined update is invalid ("cannot summon and
    move the same NPC"). Keep the valid movement and drop the summon — never crash."""
    from src.game.engine.conversation import start_conversation
    from src.game.state.autonomy import PendingNPCSummon

    state = new_game(1)
    maya = next(islander for islander in state.islanders if islander.id == "maya")
    maya.location_id = state.location_id
    start_conversation(state, "maya", state.turn_index)
    state.pending_npc_summon = PendingNPCSummon(
        npc_id="maya",
        from_conversation_id="player_active",
        reason="chemistry_partner_arrived",
        target_location=Location.POOL.value,
    )

    def move_maya(_state: GameState) -> VillaUpdate:
        return VillaUpdate(
            npc_movements=[
                NPCMovement(npc_id="maya", target_location=Location.KITCHEN, reason="drift")
            ]
        )

    villa_update, _changes, _rolls = apply_villa_turn(
        state, SeededRng(1), move_maya, background_dialogue=None, conversation_curator=None
    )

    # The valid movement survived; the conflicting summon was dropped, not crashed.
    assert villa_update.npc_summoned_elsewhere == []
    assert [m.npc_id for m in villa_update.npc_movements] == ["maya"]
    assert maya.location_id is Location.KITCHEN


def _npc_conversation() -> NPCNPCConversation:
    return NPCNPCConversation(
        id="npcconv_test",
        participants=["chloe", "maya"],
        location_id=Location.POOL,
        topic="a private chat",
        started_on_turn=1,
    )
