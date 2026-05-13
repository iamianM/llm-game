"""Opt-in tests for real Islander Voice output."""

from __future__ import annotations

import pytest

from src.game.agents.islander_voice import (
    Exchange,
    OpenAIIslanderVoice,
    islander_voice_context,
    validate_exchange,
)
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.intents import Intent, IntentCategory, load_intents
from src.game.engine.rules import apply_action
from src.game.state.models import Gender, Mood, new_game
from src.game.state.rng import SeededRng


@pytest.mark.llm
@pytest.mark.parametrize("intent", load_intents())
def test_islander_voice_output_contract(intent: Intent) -> None:
    """Real Islander Voice returns parseable, contract-valid exchanges for every intent."""
    state = new_game(1)
    for islander in state.islanders:
        islander.relationship.affection = 80
        islander.location_id = state.location_id
    target_id = "chloe"
    if intent.category is IntentCategory.BROMANCE:
        state.player.gender = Gender.MAN
        target_id = "liam"
    elif intent.category is IntentCategory.GOSSIP_RING:
        state.player.gender = Gender.WOMAN
    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id=target_id,
            intent_id=intent.id,
        ),
        SeededRng(1),
    )
    agent = OpenAIIslanderVoice()

    exchange = agent.generate(state, result)
    context = islander_voice_context(state, result)

    validate_exchange(exchange, context)
    assert context.npc_name in {"Chloe", "Liam"}


def test_islander_voice_context_includes_backstory() -> None:
    state = new_game(1)
    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(1),
    )

    context = islander_voice_context(state, result)

    assert "primary school teacher" in context.npc_backstory


def test_islander_voice_retries_after_validation_failure() -> None:
    """Validation feedback gives the model a chance to fix contract slips."""
    state = new_game(1)
    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        SeededRng(1),
    )

    class RetryVoice(OpenAIIslanderVoice):
        def __init__(self) -> None:
            super().__init__(content=None)
            self.calls = 0

        def _generate_exchange(self, rendered_context: str) -> Exchange:
            self.calls += 1
            if self.calls == 1:
                return Exchange(
                    player_dialogue="Can we talk for 2 minutes?",
                    npc_dialogue="Sure, that sounds fine.",
                    npc_tone="warm",
                    npc_mood_after=Mood.CONTENT,
                )
            assert "failed validation" in rendered_context
            return Exchange(
                player_dialogue="Can we talk for a couple of minutes?",
                npc_dialogue=(
                    "Sure, that sounds fine. I was hoping for a calmer moment by the pool anyway."
                ),
                npc_tone="warm",
                npc_mood_after=Mood.CONTENT,
            )

    agent = RetryVoice()

    exchange = agent.generate(state, result)

    assert agent.calls == 2
    assert "2" not in exchange.player_dialogue


@pytest.mark.llm
def test_islander_voice_avoids_meta_talk() -> None:
    state = new_game(1)
    state.islanders[0].relationship.affection = 80
    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="deep_ask_life",
        ),
        SeededRng(1),
    )

    exchange = OpenAIIslanderVoice().generate(state, result)
    joined = f"{exchange.player_dialogue} {exchange.npc_dialogue}".lower()

    assert "our conversation" not in joined
    assert "talking with you" not in joined
    assert "this chat" not in joined
