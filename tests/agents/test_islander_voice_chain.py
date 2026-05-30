"""Tests for Islander Voice native message-chain construction."""

from __future__ import annotations

import json

from src.game.agents.islander_voice import (
    Exchange,
    build_voice_messages,
    islander_voice_context,
    new_turn_context,
)
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.conversation import append_exchange, start_conversation
from src.game.engine.rules import apply_action
from src.game.state.models import Mood, new_game
from src.game.state.rng import SeededRng


def test_build_voice_messages_first_exchange_has_scene_and_turn() -> None:
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
    conversation = start_conversation(state, "chloe", 0)

    messages = build_voice_messages(
        state,
        conversation,
        new_turn_context(islander_voice_context(state, result)),
    )

    assert [message["role"] for message in messages] == ["user", "user"]
    assert "Backstory:" in messages[0]["content"]
    assert "Specific intent:" in messages[1]["content"]


def test_build_voice_messages_includes_prior_exchanges_as_alternating_messages() -> None:
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
    conversation = start_conversation(state, "chloe", 0)
    append_exchange(
        conversation,
        result,
        Exchange(
            player_dialogue="How are you settling in?",
            npc_dialogue="I am finding my feet by the pool.",
            npc_tone="warm",
            npc_mood_after=Mood.CONTENT,
        ),
        turn_index=0,
    )

    messages = build_voice_messages(
        state,
        conversation,
        new_turn_context(islander_voice_context(state, result)),
    )

    assert [message["role"] for message in messages] == ["user", "user", "assistant", "user"]
    prior = json.loads(messages[2]["content"])
    assert prior["player_dialogue"] == "How are you settling in?"
    assert prior["npc_tone"] == "warm"


def test_build_voice_messages_injects_anti_repetition_guard_after_prior_exchanges() -> None:
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
    conversation = start_conversation(state, "chloe", 0)
    append_exchange(
        conversation,
        result,
        Exchange(
            player_dialogue="You don't have to carry all of it alone.",
            npc_dialogue="*softens* You're not as guarded as you pretend.",
            npc_tone="warm",
            npc_mood_after=Mood.CONTENT,
        ),
        turn_index=0,
    )

    messages = build_voice_messages(
        state,
        conversation,
        new_turn_context(islander_voice_context(state, result)),
    )

    # Message count and roles are unchanged so the chain contract still holds.
    assert [message["role"] for message in messages] == ["user", "user", "assistant", "user"]
    final = messages[-1]["content"]
    assert "Anti-repetition guard." in final
    assert '"You don\'t have to carry all"' in final
    assert '"You\'re not as guarded as you"' in final  # leading *softens* is stripped
    # The guard names banned opener shapes explicitly so the weak model can
    # recognize them — including the reassurance frame, not just greetings.
    assert "generic greeting frame" in final
    assert "reassurance frame" in final
    assert "you don't have to perform/pretend with me" in final
    # The write cue stays last so the model still knows to act now.
    assert final.rstrip().endswith("Write the exchange now.")


def test_build_voice_messages_no_guard_for_fresh_conversation() -> None:
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
    conversation = start_conversation(state, "chloe", 0)

    messages = build_voice_messages(
        state,
        conversation,
        new_turn_context(islander_voice_context(state, result)),
    )

    assert "Anti-repetition guard." not in messages[-1]["content"]


def test_build_voice_messages_guards_against_cross_conversation_openers() -> None:
    # A fresh conversation has no prior exchanges of its own, but the villa-wide
    # recent-player-lines buffer carries the opener used with the last islander.
    # Without this, the one-at-a-time intro round greets everyone identically.
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
    state.recent_player_lines = ["Thought I'd come say hi properly while it's still calm."]
    conversation = start_conversation(state, "chloe", 0)

    messages = build_voice_messages(
        state,
        conversation,
        new_turn_context(islander_voice_context(state, result)),
    )

    final = messages[-1]["content"]
    assert "Anti-repetition guard." in final
    assert '"Thought I\'d come say hi properly"' in final
    assert final.rstrip().endswith("Write the exchange now.")


def test_new_turn_message_includes_intent_and_outcome() -> None:
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

    messages = build_voice_messages(
        state,
        None,
        new_turn_context(islander_voice_context(state, result)),
    )

    assert "Friendly" in messages[-1]["content"] or "friendly" in messages[-1]["content"]
    assert "Mechanical outcome:" in messages[-1]["content"]
