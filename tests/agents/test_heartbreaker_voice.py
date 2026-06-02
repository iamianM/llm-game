"""Opt-in tests for real Heartbreaker Voice output."""

from __future__ import annotations

import pytest

from src.game.agents.heartbreaker_voice import (
    Exchange,
    OpenAIHeartbreakerVoice,
    heartbreaker_voice_context,
    validate_exchange,
)
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.intents import Intent, IntentCategory, load_intents
from src.game.engine.private_chat import PrivateChatAttempt
from src.game.engine.results import MechanicalResult
from src.game.engine.rules import apply_action
from src.game.state.models import Gender, Mood, new_game
from src.game.state.rng import SeededRng


@pytest.mark.llm
@pytest.mark.parametrize("intent", load_intents())
def test_heartbreaker_voice_output_contract(intent: Intent) -> None:
    """Real Heartbreaker Voice returns parseable, contract-valid exchanges for every intent."""
    state = new_game(1)
    for heartbreaker in state.heartbreakers:
        heartbreaker.relationship.affection = 80
        heartbreaker.location_id = state.location_id
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
    agent = OpenAIHeartbreakerVoice()

    exchange = agent.generate(state, result)
    context = heartbreaker_voice_context(state, result)

    validate_exchange(exchange, context)
    assert context.npc_name in {"Chloe", "Liam"}


def test_heartbreaker_voice_context_includes_backstory() -> None:
    state = new_game(1)
    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        SeededRng(1),
    )

    context = heartbreaker_voice_context(state, result)

    assert "primary school teacher" in context.npc_backstory


def test_heartbreaker_voice_context_signals_established_rapport() -> None:
    """A high-familiarity target should be flagged as already-known so the opener
    of a re-started conversation does not cold-open like a first meeting."""
    state = new_game(1)
    chloe = next(heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == "chloe")
    chloe.familiarity_with_player = 70
    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        SeededRng(1),
    )

    context = heartbreaker_voice_context(state, result)

    assert "familiarity 70/100" in context.relationship_summary
    assert "know the player well" in context.relationship_summary
    assert "stranger" in context.relationship_summary


def test_heartbreaker_voice_context_signals_fresh_introduction() -> None:
    """A near-zero-familiarity target keeps the early getting-to-know-you framing
    so genuine first meetings still open like first meetings."""
    state = new_game(1)
    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        SeededRng(1),
    )

    context = heartbreaker_voice_context(state, result)

    assert "barely know the player yet" in context.relationship_summary


def test_heartbreaker_voice_retries_after_validation_failure() -> None:
    """Validation feedback gives the model a chance to fix contract slips."""
    state = new_game(1)
    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        SeededRng(1),
    )

    class RetryVoice(OpenAIHeartbreakerVoice):
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


def test_heartbreaker_voice_redraws_reused_opener() -> None:
    """A player line that reopens with an already-used opening is re-prompted
    once, and the re-prompt names the offending opening so the model can vary
    only the opener while keeping the same intent."""
    state = new_game(1)
    state.recent_player_lines = ["You don't need to have it all mapped out, Chloe."]
    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        SeededRng(1),
    )

    class StaleThenFresh(OpenAIHeartbreakerVoice):
        def __init__(self) -> None:
            super().__init__(content=None)
            self.calls = 0

        def _generate_exchange(self, rendered_context: object) -> Exchange:
            self.calls += 1
            if self.calls == 1:
                return Exchange(
                    player_dialogue="You don't need to have it all sorted out, Chloe.",
                    npc_dialogue="That's kind of you to say, it does settle me a bit.",
                    npc_tone="warm",
                    npc_mood_after=Mood.CONTENT,
                )
            assert isinstance(rendered_context, list)
            assert "You don't need to have it" in rendered_context[-1]["content"]
            return Exchange(
                player_dialogue="Honestly, the way you read this place is a bit unreal.",
                npc_dialogue="Ha, I clock everything. Force of habit from the classroom.",
                npc_tone="amused",
                npc_mood_after=Mood.HAPPY,
            )

    agent = StaleThenFresh()

    exchange = agent.generate(state, result)

    assert agent.calls == 2
    assert exchange.player_dialogue.startswith("Honestly")


def test_heartbreaker_voice_accepts_best_effort_when_opener_keeps_repeating() -> None:
    """A stubbornly repeated opener never degrades to mock dialogue: after the
    retries are spent the last structurally valid exchange is returned as-is."""
    state = new_game(1)
    state.recent_player_lines = ["You don't need to have it all mapped out, Chloe."]
    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        SeededRng(1),
    )

    class AlwaysStale(OpenAIHeartbreakerVoice):
        def __init__(self) -> None:
            super().__init__(content=None)
            self.calls = 0

        def _generate_exchange(self, rendered_context: object) -> Exchange:
            self.calls += 1
            return Exchange(
                player_dialogue="You don't need to have it all figured out yet, Chloe.",
                npc_dialogue="I know, I just hate feeling like I'm behind everyone.",
                npc_tone="vulnerable",
                npc_mood_after=Mood.CONTENT,
            )

    agent = AlwaysStale()

    exchange = agent.generate(state, result)

    assert agent.calls == 3
    assert exchange.player_dialogue.startswith("You don't need to have it")


def test_heartbreaker_voice_context_identifies_player_as_listener() -> None:
    state = new_game(1)
    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        SeededRng(1),
    )

    from src.game.agents.heartbreaker_voice_context import build_voice_messages, new_turn_context

    context = heartbreaker_voice_context(state, result)
    messages = build_voice_messages(state, state.active_conversation, new_turn_context(context))

    assert "Conversation partner: the player" in messages[0]["content"]


def test_heartbreaker_voice_context_includes_successful_private_chat() -> None:
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="maya",
            intent_id="flirty_intimate_eye_contact",
        ),
        success=True,
        tags=["flirty", "intense"],
        private_chat_attempt=PrivateChatAttempt(
            target_id="maya",
            started_from_location="pool",
            success=True,
            chance=77,
            roll=18,
            blocked_conversation_id="npcconv_maya_liam_pool",
            blocked_participants=["maya", "liam"],
            blocked_topic="Maya and Liam comparing notes on the early couples",
        ),
    )

    from src.game.agents.heartbreaker_voice_context import new_turn_context

    context = heartbreaker_voice_context(state, result)
    turn = new_turn_context(context)

    assert context.private_chat_context is not None
    assert "opened a private chat with Maya" in turn.turn
    assert "comparing notes on the early couples" in turn.turn


def test_heartbreaker_voice_allows_gossip_subject_mentions() -> None:
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.RESPOND_WITH,
            target_id="chloe",
            intent_id="ask_gossip:about_blake",
        ),
        success=True,
        tags=["gossip"],
    )

    context = heartbreaker_voice_context(state, result)
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


def test_heartbreaker_voice_rejects_flush_of_hearts_brand_leak() -> None:
    """The second resort is branded "Flush of Hearts"; source-show wording fails."""
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(kind=ActionKind.RESPOND_WITH, target_id="chloe", intent_id="banter_tell_joke"),
        success=True,
    )
    context = heartbreaker_voice_context(state, result)
    retired_term = "Flush " + "Amor"
    leaked = Exchange(
        player_dialogue=f"You look far too sweet to survive {retired_term}, Chloe.",
        npc_dialogue="Cheeky! I will take that as a compliment and a warning.",
        npc_tone="playful",
        npc_mood_after=Mood.FLIRTY,
    )

    with pytest.raises(ValueError, match="retired source-show term"):
        validate_exchange(leaked, context)

    # The branded phrasing passes cleanly.
    branded = leaked.model_copy(
        update={"player_dialogue": "You look far too sweet to survive the Flush of Hearts, Chloe."}
    )
    validate_exchange(branded, context)


def test_heartbreaker_voice_allows_share_gossip_subject_mentions() -> None:
    """Sharing a player memory whitelists its subject so the natural mention
    of that subject does not trip validate_exchange (the live share_gossip
    'That choice did not land' crash)."""
    from src.game.engine.memory import add_memory, create_memory

    state = new_game(1)
    memory = create_memory(
        holder_id="player",
        subject_id="maya",
        source="witnessed",
        day=1,
        turn=1,
        weight=7,
        tags=["gossip"],
        content="Maya looked rattled after Liam stepped back.",
    )
    add_memory(state, memory)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.RESPOND_WITH,
            target_id="chloe",
            intent_id=f"share_gossip:{memory.id}",
        ),
        success=True,
        tags=["gossip"],
    )

    context = heartbreaker_voice_context(state, result)
    exchange = Exchange(
        player_dialogue="Chloe, can I tell you something? I saw Maya look really rattled earlier.",
        npc_dialogue=(
            "Oh? I had not clocked that about Maya. Tell me what you noticed, I am listening."
        ),
        npc_tone="warm",
        npc_mood_after=Mood.CONTENT,
    )

    # The subject (Maya) plus any other cast named in the gossip content (Liam)
    # are whitelisted, so the NPC can echo either without tripping the leak guard.
    assert context.gossip_subject_names == ["Maya", "Liam"]
    assert context.intent_category == "gossip"
    validate_exchange(exchange, context)


def test_heartbreaker_voice_allows_share_gossip_mentioning_absent_second_cast() -> None:
    """Real gossip often names more than its subject (e.g. "Maya and Jordan").
    Every cast member named in the gossip content must be whitelisted, even when
    absent, or the NPC echoing the second name dead-screens the turn."""
    from src.game.engine.memory import add_memory, create_memory

    state = new_game(1)
    memory = create_memory(
        holder_id="player",
        subject_id="maya",
        source="witnessed",
        day=1,
        turn=1,
        weight=7,
        tags=["gossip"],
        content="I watched Maya and Blake trade cheeky lines in the kitchen.",
    )
    add_memory(state, memory)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.RESPOND_WITH,
            target_id="chloe",
            intent_id=f"share_gossip:{memory.id}",
        ),
        success=True,
        tags=["gossip"],
    )

    context = heartbreaker_voice_context(state, result)
    # Blake is absent (not in the conversation) but is named in the gossip the
    # player is sharing, so the NPC may mention them back without it counting as
    # a leaked hidden Heartbreaker.
    assert "Blake" in context.gossip_subject_names
    assert "Blake" not in context.others_present
    exchange = Exchange(
        player_dialogue="I saw Maya and Blake flirting in the kitchen earlier.",
        npc_dialogue="Oh, Maya and Blake? *grins* I had a feeling about those two.",
        npc_tone="amused",
        npc_mood_after=Mood.HAPPY,
    )
    validate_exchange(exchange, context)


def test_heartbreaker_voice_context_supplies_cast_pronouns() -> None:
    """The voice gets a pronoun roster so unisex third-party names are not guessed.

    ``cast_names``/``others_present`` are matched verbatim by the leak validator,
    so the gender signal rides on a separate ``cast_pronouns`` roster that the
    turn block surfaces for every living heartbreaker."""
    from src.game.agents.heartbreaker_voice_context import new_turn_context

    state = new_game(1)
    chloe = next(i for i in state.heartbreakers if i.id == "chloe")
    liam = next(i for i in state.heartbreakers if i.id == "liam")
    assert chloe.gender is Gender.WOMAN
    assert liam.gender is Gender.MAN

    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        SeededRng(1),
    )
    context = heartbreaker_voice_context(state, result)

    assert f"{chloe.name}: she/her" in context.cast_pronouns
    assert f"{liam.name}: he/him" in context.cast_pronouns

    turn = new_turn_context(context).turn
    assert "Cast pronouns (use exactly these" in turn
    assert f"{liam.name}: he/him" in turn


def test_heartbreaker_voice_cast_pronouns_exclude_eliminated() -> None:
    """A Heart Out heartbreaker should drop off the live pronoun roster."""
    state = new_game(1)
    target = next(i for i in state.heartbreakers if i.id == "chloe")
    eliminated = next(i for i in state.heartbreakers if i.id == "maya")
    eliminated.eliminated = True

    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id=target.id,
            intent_id="friendly_chat_resort",
        ),
        SeededRng(1),
    )
    context = heartbreaker_voice_context(state, result)

    roster_names = {entry.split(":")[0] for entry in context.cast_pronouns}
    assert eliminated.name not in roster_names
    assert target.name in roster_names


@pytest.mark.llm
def test_heartbreaker_voice_avoids_meta_talk() -> None:
    state = new_game(1)
    state.heartbreakers[0].relationship.affection = 80
    result = apply_action(
        state,
        PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="deep_ask_life",
        ),
        SeededRng(1),
    )

    exchange = OpenAIHeartbreakerVoice().generate(state, result)
    joined = f"{exchange.player_dialogue} {exchange.npc_dialogue}".lower()

    assert "our conversation" not in joined
    assert "talking with you" not in joined
    assert "this chat" not in joined
