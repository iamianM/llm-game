"""Opt-in tests for private-chat-rejection Heartbreaker Voice exchanges."""

from __future__ import annotations

import pytest

from src.game.agents.heartbreaker_voice import OpenAIHeartbreakerVoice
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.private_chat import PrivateChatAttempt
from src.game.engine.rules import MechanicalResult
from src.game.state.models import (
    AttachmentStyle,
    Big5,
    Gender,
    HeartbreakerState,
    IdealMatch,
    Location,
    RelationshipDelta,
    RelationshipState,
    new_game,
)


@pytest.mark.llm
@pytest.mark.parametrize(
    ("target_id", "name", "archetype"),
    [
        ("chloe", "Chloe", "sweetheart"),
        ("maya", "Maya", "joker"),
        ("liam", "Liam", "friend"),
        ("aisha", "Aisha", "joker"),
    ],
)
def test_heartbreaker_voice_private_chat_rejected_deflects_busy_target(
    target_id: str,
    name: str,
    archetype: str,
) -> None:
    """Private chat rejection output is in voice and does not warmly accept the private chat."""
    state = new_game(1)
    for heartbreaker in state.heartbreakers:
        heartbreaker.location_id = Location.POOL
    if target_id == "aisha":
        state.heartbreakers.append(
            HeartbreakerState(
                id="aisha",
                name=name,
                gender=Gender.WOMAN,
                archetype=archetype,
                backstory="Aisha is a bold Heart Throb who tests whether stable couples can survive pressure.",
                location_id=Location.POOL,
                relationship=RelationshipState(affection=15),
                big5=Big5(openness=9, conscientiousness=4, extraversion=9, agreeableness=5, neuroticism=5),
                attachment=AttachmentStyle.AVOIDANT,
                ideal_match=IdealMatch(
                    physical_type="confident eye contact",
                    personality_type=["bold", "unpredictable"],
                    values=["chemistry", "confidence"],
                    dealbreakers=["neediness"],
                ),
            )
        )
    target = next(heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == target_id)
    target.name = name
    target.archetype = archetype
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id=target_id,
            intent_id="private_chat_rejected",
        ),
        success=False,
        roll=88,
        success_chance=35,
        relationship_deltas={target_id: RelationshipDelta(affection=-1)},
        tags=["private_chat_rejected"],
        private_chat_attempt=PrivateChatAttempt(
            target_id=target_id,
            started_from_location=Location.POOL,
            success=False,
            chance=35,
            roll=88,
            blocked_conversation_id="npcconv_busy",
        ),
    )

    exchange = OpenAIHeartbreakerVoice().generate(state, result)

    joined = f"{exchange.player_dialogue} {exchange.npc_dialogue}".lower()
    assert any(
        phrase in joined
        for phrase in (
            "busy",
            "talking",
            "conversation",
            "later",
            "middle",
            "not right now",
            "another time",
            "finish",
            "wait",
            "after",
            "a bit",
            "give me",
        )
    )
