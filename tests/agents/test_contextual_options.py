"""Opt-in tests for real Contextual Options output."""

from __future__ import annotations

from typing import Literal

import pytest

from src.game.agents.contextual_options import ContextualOptionsAgent, validate_follow_up_menu
from src.game.agents.islander_voice import Exchange
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.rules import MechanicalResult
from src.game.state.models import Mood, RelationshipDelta, new_game

Tone = Literal["warm", "flirty", "suspicious", "amused", "cold", "vulnerable", "playful", "defensive"]


@pytest.mark.llm
@pytest.mark.parametrize(
    ("departure_probability", "tone"),
    [
        (0, "warm"),
        (15, "flirty"),
        (30, "playful"),
        (45, "vulnerable"),
        (60, "defensive"),
        (70, "suspicious"),
        (80, "cold"),
        (90, "defensive"),
        (100, "cold"),
        (100, "suspicious"),
    ],
)
def test_contextual_options_contract(departure_probability: int, tone: Tone) -> None:
    """Contextual Options returns a validated menu for varied departure pressure."""
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        success=tone in {"warm", "flirty", "playful", "vulnerable"},
        relationship_deltas={"chloe": RelationshipDelta(affection=2)},
        tags=["friendly"],
    )
    exchange = Exchange(
        player_dialogue="I wanted to check in properly and see where your head is at.",
        npc_dialogue="I appreciate that, but I am still deciding how much I want to open up right now.",
        npc_tone=tone,
        npc_mood_after=Mood.CONTENT,
    )
    agent = ContextualOptionsAgent()

    menu = agent.generate(state, result, exchange, departure_probability)

    validate_follow_up_menu(menu)
    if departure_probability == 0:
        assert menu.npc_will_leave is False
    if departure_probability == 100:
        assert menu.npc_will_leave is True
