"""Tests for orchestrator NPC summoning."""

from __future__ import annotations

import pytest

from src.game.agents.resort_orchestrator import NPCSummon, ResortUpdate
from src.game.engine.conversation import departure_probability, start_conversation
from src.game.engine.resort import apply_resort_update, validate_resort_update
from src.game.state.models import (
    BackgroundExchangeRecord,
    ExchangeRecord,
    Location,
    Mood,
    NPCNPCConversation,
    RelationshipDelta,
    new_game,
)
from src.game.state.personality import AttachmentStyle
from src.game.state.rng import SeededRng


def test_validate_summon_requires_named_conversation_participant() -> None:
    state = new_game(1)

    with pytest.raises(ValueError, match="player_active summon"):
        validate_resort_update(
            state,
            ResortUpdate(
                npc_summoned_elsewhere=[
                    NPCSummon(
                        npc_id="maya",
                        from_conversation_id="player_active",
                        reason="needs_space",
                        target_location=Location.TERRACE,
                    )
                ]
            ),
        )


def test_apply_summon_closes_player_conversation_and_runs_curator() -> None:
    state = new_game(1)
    start_conversation(state, "chloe", 1)

    changes = apply_resort_update(
        state,
        ResortUpdate(
            npc_summoned_elsewhere=[
                NPCSummon(
                    npc_id="chloe",
                    from_conversation_id="player_active",
                    reason="needs_space",
                    target_location=Location.TERRACE,
                )
            ]
        ),
        SeededRng(1),
    )

    assert state.active_conversation is None
    assert state.heartbreakers[0].location_id is Location.TERRACE
    assert changes.curator_batches
    assert changes.curator_batches[0].kind == "player"


def test_apply_summon_closes_npc_npc_conversation() -> None:
    state = new_game(1)
    conversation = NPCNPCConversation(
        id="npcconv_test",
        participants=["maya", "liam"],
        location_id=Location.KITCHEN,
        topic="breakfast flirting",
        started_on_turn=1,
        exchanges=[
            BackgroundExchangeRecord(
                turn_index=1,
                speaker_a_id="maya",
                speaker_b_id="liam",
                speaker_a_line="Nice pancakes.",
                speaker_b_line="You noticed.",
                tone="flirty",
            )
        ],
    )
    state.heartbreakers[1].location_id = Location.KITCHEN
    state.heartbreakers[2].location_id = Location.KITCHEN
    state.npc_conversations = [conversation]

    changes = apply_resort_update(
        state,
        ResortUpdate(
            npc_summoned_elsewhere=[
                NPCSummon(
                    npc_id="maya",
                    from_conversation_id="npcconv_test",
                    reason="drama_summon",
                    target_location=Location.POOL,
                )
            ]
        ),
        SeededRng(1),
    )

    assert state.npc_conversations == []
    assert state.heartbreakers[1].location_id is Location.POOL
    assert changes.curator_batches
    assert changes.curator_batches[0].kind == "background"


def test_departure_probability_increases_for_avoidant_deep_exchange() -> None:
    state = new_game(1)
    chloe = state.heartbreakers[0]
    chloe.attachment = AttachmentStyle.AVOIDANT
    conversation = start_conversation(state, "chloe", 1)
    conversation.exchanges = [_exchange(success=True, tags=["deep"]) for _ in range(11)]

    assert departure_probability(conversation, state) >= 20


def test_departure_probability_increases_for_anxious_miss() -> None:
    state = new_game(1)
    maya = state.heartbreakers[1]
    maya.attachment = AttachmentStyle.ANXIOUS
    conversation = start_conversation(state, "maya", 1)
    conversation.exchanges.append(_exchange(success=False, tags=["banter"]))

    assert departure_probability(conversation, state) >= 33


def _exchange(*, success: bool, tags: list[str]) -> ExchangeRecord:
    return ExchangeRecord(
        turn_index=1,
        intent_id="test",
        player_dialogue="Hello.",
        npc_dialogue="Hi.",
        npc_tone="content",
        npc_mood_after=Mood.CONTENT,
        success=success,
        tags=tags,
        relationship_deltas={"chloe": RelationshipDelta()},
    )
