"""Opt-in tests for real Islander Voice output."""

from __future__ import annotations

import pytest

from src.game.agents.islander_voice import (
    OpenAIIslanderVoice,
    islander_voice_context,
    validate_exchange,
)
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.intents import Intent, load_intents
from src.game.engine.rules import apply_action
from src.game.state.models import new_game
from src.game.state.rng import SeededRng


@pytest.mark.llm
@pytest.mark.parametrize("intent", load_intents())
def test_islander_voice_output_contract(intent: Intent) -> None:
    """Real Islander Voice returns parseable, contract-valid exchanges for every intent."""
    state = new_game(1)
    for islander in state.islanders:
        islander.relationship.affection = 80
        islander.location_id = state.location_id
    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id=intent.id,
        ),
        SeededRng(1),
    )
    agent = OpenAIIslanderVoice()

    exchange = agent.generate(state, result)
    context = islander_voice_context(state, result)

    validate_exchange(exchange, context)
    assert context.npc_name == "Chloe"
