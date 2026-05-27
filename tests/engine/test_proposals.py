"""Tests for recoupling proposal mechanics."""

from __future__ import annotations

from src.game.agents.background_dialogue import BackgroundExchange
from src.game.agents.villa_orchestrator import EndConversation, VillaUpdate
from src.game.engine.actions import ActionKind, PlayerAction, available_actions
from src.game.engine.proposals import apply_player_proposal, maybe_trigger_npc_player_proposal
from src.game.engine.turn import run_turn
from src.game.engine.villa import apply_villa_update
from src.game.state.models import (
    BackgroundExchangeRecord,
    Conversation,
    Couple,
    Gender,
    Location,
    NPCNPCConversation,
    PendingRecoupleProposal,
    new_game,
)
from src.game.state.rng import SeededRng


def test_player_proposal_action_surfaces_only_for_eligible_non_partner() -> None:
    state = _proposal_state()
    state.active_conversation = Conversation(target_id="maya", started_on_turn=1, started_on_day=1)

    labels = [spec.label for spec in available_actions(state)]

    assert "Ask Maya to recouple with you" in labels


def test_successful_player_proposal_breaks_old_couples_and_leaves_singles() -> None:
    state = _proposal_state()

    result, outcome = apply_player_proposal(state, "maya", SeededRng(1))

    assert result.success is True
    assert outcome.old_player_partner_id == "chloe"
    assert outcome.old_target_partner_id == "liam"
    assert [(couple.partner_a_id, couple.partner_b_id, couple.formed_via) for couple in state.couples] == [
        ("player", "maya", "proposal")
    ]
    assert _partner_id(state, "chloe") is None
    assert _partner_id(state, "liam") is None


def test_rejected_player_proposal_keeps_couples_and_hits_audience() -> None:
    state = _proposal_state()

    result, outcome = apply_player_proposal(state, "maya", SeededRng(5))

    assert result.success is False
    assert outcome.accepted is False
    assert [(couple.partner_a_id, couple.partner_b_id) for couple in state.couples] == [
        ("player", "chloe"),
        ("maya", "liam"),
    ]
    assert result.audience_delta < 0
    assert state.islanders[1].relationship.affection == 50
    assert state.islanders[1].relationship.chemistry == 65


def test_proposal_turn_closes_conversation_and_records_event_and_memories() -> None:
    state = _proposal_state()
    state.active_conversation = Conversation(target_id="maya", started_on_turn=1, started_on_day=1)

    turn = run_turn(state, PlayerAction(kind=ActionKind.PROPOSE_RECOUPLE, target_id="maya"), SeededRng(1))

    assert turn.state.active_conversation is None
    assert turn.ceremony_events[0].kind == "recouple_proposal"
    assert turn.ceremony_events[0].sub_kind == "accepted"
    assert any(batch.summary.startswith("Player proposed") for batch in turn.curator_batches)


def test_npc_proposal_incoming_creates_forced_response_actions() -> None:
    state = _proposal_state()
    state.active_conversation = None
    maya = state.islanders[1]
    maya.relationship.affection = 80
    maya.relationship.chemistry = 90

    incoming = maybe_trigger_npc_player_proposal(state, SeededRng(1))

    assert incoming is not None
    labels = [spec.label for spec in available_actions(state)]
    assert labels == [
        "Accept Maya's recoupling proposal",
        "Decline Maya politely",
        "Decline Maya harshly",
    ]


def test_accepting_npc_proposal_forms_new_couple_and_leaves_singles() -> None:
    state = _proposal_state()
    state.active_conversation = None
    state.islanders[1].relationship.affection = 80
    state.islanders[1].relationship.chemistry = 90
    maybe_trigger_npc_player_proposal(state, SeededRng(1))

    turn = run_turn(
        state,
        PlayerAction(kind=ActionKind.NPC_PROPOSAL_RESPONSE, target_id="maya", intent_id="accept"),
        SeededRng(2),
    )

    assert turn.state.pending_recouple_proposal is None
    assert _partner_id(state, "player") == "maya"
    assert _partner_id(state, "chloe") is None
    assert _partner_id(state, "liam") is None
    assert turn.ceremony_events[0].kind == "npc_proposal_response"


def test_npc_proposal_response_does_not_reopen_same_turn() -> None:
    state = _proposal_state()
    state.active_conversation = None
    maya = state.islanders[1]
    maya.relationship.affection = 80
    maya.relationship.chemistry = 90
    state.pending_recouple_proposal = PendingRecoupleProposal(
        proposer_id="maya",
        chance=60,
        audience_hint_accept="",
    )

    turn = run_turn(
        state,
        PlayerAction(kind=ActionKind.NPC_PROPOSAL_RESPONSE, target_id="maya", intent_id="decline_harshly"),
        SeededRng(4),
    )

    assert turn.state.pending_recouple_proposal is None
    assert [event.kind for event in turn.ceremony_events] == ["npc_proposal_response"]


def test_single_npc_background_flirt_can_form_rebound_couple() -> None:
    state = new_game(1)
    state.couples = []
    conversation = NPCNPCConversation(
        id="npcconv_test",
        participants=["maya", "liam"],
        location_id=Location.TERRACE,
        topic="testing the spark",
        started_on_turn=1,
        exchanges=[
            BackgroundExchangeRecord(
                turn_index=1,
                speaker_a_id="maya",
                speaker_b_id="liam",
                speaker_a_line="one",
                speaker_b_line="two",
                tone="flirty",
            ),
            BackgroundExchangeRecord(
                turn_index=2,
                speaker_a_id="maya",
                speaker_b_id="liam",
                speaker_a_line="three",
                speaker_b_line="four",
                tone="flirty",
            ),
        ],
    )
    state.npc_conversations = [conversation]

    changes = apply_villa_update(
        state,
        VillaUpdate(conversation_ends=[EndConversation(conversation_id="npcconv_test", reason="spark")]),
        SeededRng(1),
        background_dialogue=lambda _state, _conversation, _nudge: BackgroundExchange(
            speaker_a_line="",
            speaker_b_line="",
            tone="neutral",
        ),
    )

    assert _partner_id(state, "maya") == "liam"
    assert state.couples[0].rebound is True
    assert any(batch.summary.startswith("Maya and Liam") for batch in changes.curator_batches)


def _proposal_state():
    state = new_game(1)
    state.player.gender = Gender.MAN
    state.couples = [
        Couple(partner_a_id="player", partner_b_id="chloe", formed_on_day=1),
        Couple(partner_a_id="maya", partner_b_id="liam", formed_on_day=1),
    ]
    maya = state.islanders[1]
    assert maya.id == "maya"
    maya.relationship.affection = 55
    maya.relationship.chemistry = 70
    maya.relationship.trust = 10
    return state


def _partner_id(state, actor_id: str) -> str | None:
    for couple in state.couples:
        if couple.partner_a_id == actor_id:
            return couple.partner_b_id
        if couple.partner_b_id == actor_id:
            return couple.partner_a_id
    return None
