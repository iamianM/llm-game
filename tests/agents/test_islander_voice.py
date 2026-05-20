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
from src.game.engine.results import MechanicalResult
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

        def _generate_exchange(self, rendered_context: object) -> Exchange:
            self.calls += 1
            if self.calls == 1:
                return Exchange(
                    player_dialogue=(
                        "I wanted to come find you. I was thinking about what Maya said earlier and "
                        "honestly it stuck with me more than I expected."
                    ),
                    npc_dialogue=(
                        "I noticed you looked thoughtful. Liam was watching the same conversation, "
                        "I think it shifted something in him too."
                    ),
                    npc_tone="warm",
                    npc_mood_after=Mood.CONTENT,
                )
            assert isinstance(rendered_context, list)
            assert "failed validation" in rendered_context[-1]["content"]
            return Exchange(
                player_dialogue=(
                    "I wanted to come find you. I was thinking about you and how the day landed."
                ),
                npc_dialogue=(
                    "I noticed you looked thoughtful out there, and I was hoping you would come "
                    "sit with me before the sun dropped."
                ),
                npc_tone="warm",
                npc_mood_after=Mood.CONTENT,
            )

    agent = RetryVoice()

    exchange = agent.generate(state, result)

    assert agent.calls == 2
    assert "Maya" not in exchange.player_dialogue and "Maya" not in exchange.npc_dialogue
    assert "Liam" not in exchange.player_dialogue and "Liam" not in exchange.npc_dialogue


def test_islander_voice_context_identifies_player_as_listener() -> None:
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

    from src.game.agents.islander_voice_context import build_voice_messages, new_turn_context

    context = islander_voice_context(state, result)
    messages = build_voice_messages(state, state.active_conversation, new_turn_context(context))

    assert "Conversation partner: the player" in messages[0]["content"]


def test_islander_voice_allows_gossip_subject_mentions() -> None:
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.RESPOND_WITH,
            target_id="chloe",
            intent_id="ask_gossip:about_blake_start",
        ),
        success=True,
        tags=["gossip"],
    )

    context = islander_voice_context(state, result)
    exchange = Exchange(
        player_dialogue="What do you make of Blake so far, Chloe? I want your honest read.",
        npc_dialogue=(
            "Blake seems polished, and I am not fully sure what sits under it yet. "
            "I would keep watching before trusting the charm too much."
        ),
        npc_tone="warm",
        npc_mood_after=Mood.CONTENT,
    )

    assert context.gossip_subject_names == ["Blake"]
    validate_exchange(exchange, context)


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
