"""Opt-in tests for pull-rejection Islander Voice exchanges."""

from __future__ import annotations

import pytest

from src.game.agents.islander_voice import OpenAIIslanderVoice
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.pull import PullAttempt
from src.game.engine.rules import MechanicalResult
from src.game.state.models import (
    AttachmentStyle,
    Big5,
    IslanderState,
    Location,
    RelationshipDelta,
    RelationshipState,
    TypeOnPaper,
    new_game,
)


@pytest.mark.llm
@pytest.mark.parametrize(
    ("target_id", "name", "archetype"),
    [
        ("chloe", "Chloe", "sweetheart"),
        ("maya", "Maya", "joker"),
        ("liam", "Liam", "friend"),
        ("aisha", "Aisha", "bombshell"),
    ],
)
def test_islander_voice_pull_rejected_deflects_busy_target(
    target_id: str,
    name: str,
    archetype: str,
) -> None:
    """Pull rejection output is in voice and does not warmly accept the pull."""
    state = new_game(1)
    for islander in state.islanders:
        islander.location_id = Location.POOL
    if target_id == "aisha":
        state.islanders.append(
            IslanderState(
                id="aisha",
                name=name,
                archetype=archetype,
                location_id=Location.POOL,
                relationship=RelationshipState(affection=15),
                big5=Big5(openness=9, conscientiousness=4, extraversion=9, agreeableness=5, neuroticism=5),
                attachment=AttachmentStyle.AVOIDANT,
                type_on_paper=TypeOnPaper(
                    physical_type="confident eye contact",
                    personality_type=["bold", "unpredictable"],
                    values=["chemistry", "confidence"],
                    dealbreakers=["neediness"],
                ),
            )
        )
    target = next(islander for islander in state.islanders if islander.id == target_id)
    target.name = name
    target.archetype = archetype
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id=target_id,
            intent_id="pull_rejected",
        ),
        success=False,
        roll=88,
        success_chance=35,
        relationship_deltas={target_id: RelationshipDelta(affection=-1)},
        tags=["pull_rejected"],
        pull_attempt=PullAttempt(
            target_id=target_id,
            started_from_location=Location.POOL,
            success=False,
            chance=35,
            roll=88,
            blocked_conversation_id="npcconv_busy",
        ),
    )

    exchange = OpenAIIslanderVoice().generate(state, result)

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
