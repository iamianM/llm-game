"""Tests for Contextual Options output and runtime wheel validation."""

from __future__ import annotations

from typing import Literal

import pytest

from src.game.agents.contextual_options import (
    ContextualBespoke,
    ContextualOptionsAgent,
    contextual_options_context,
    mock_follow_up_menu,
    validate_contextual_bespoke,
    validate_follow_up_menu,
)
from src.game.agents.heartbreaker_voice import Exchange
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.follow_up_menu import generate_follow_up_menu
from src.game.engine.private_chat import PrivateChatAttempt
from src.game.engine.rules import MechanicalResult
from src.game.state.memory import RecapDisposition
from src.game.state.models import FollowUpOption, Memory, Mood, RelationshipDelta, new_game

Tone = Literal[
    "warm", "flirty", "suspicious", "amused", "cold", "vulnerable", "playful", "defensive"
]


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
            intent_id="friendly_chat_resort",
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

    bespoke = agent.generate(
        state,
        result,
        exchange,
        departure_probability,
        already_present=[
            FollowUpOption(
                label="End on a good note",
                category="exit",
                intent_kind="end_softly",
                stat_used=None,
                risk="safe",
                tone="warm",
            ),
            FollowUpOption(
                label="Apologize honestly",
                category="supportive",
                intent_kind="apologize",
                stat_used="eq",
                risk="safe",
                tone="apologetic",
            ),
        ],
    )

    validate_contextual_bespoke(bespoke, ["end_softly", "apologize"])
    if departure_probability == 0:
        assert bespoke.npc_will_leave is False
    if departure_probability == 100:
        assert bespoke.npc_will_leave is True


def test_assembled_menu_adds_exit_to_bespoke_output() -> None:
    """The engine keeps one exit wheel option around bespoke additions."""
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        success=True,
        relationship_deltas={"chloe": RelationshipDelta(affection=2)},
        tags=["friendly"],
    )
    exchange = Exchange(
        player_dialogue="I wanted to check in properly.",
        npc_dialogue="I appreciate that.",
        npc_tone="warm",
        npc_mood_after=Mood.CONTENT,
    )

    def contextual_options(*_args, **_kwargs) -> ContextualBespoke:
        return ContextualBespoke(
            options=[
                FollowUpOption(
                    label="Ask why Liverpool matters",
                    category="deep",
                    intent_kind="go_deeper",
                    stat_used="eq",
                    risk="medium",
                    tone="curious",
                ),
                FollowUpOption(
                    label="Tease the Sunset Bay tension",
                    category="banter",
                    intent_kind="joke_back",
                    stat_used="banter",
                    risk="low",
                    tone="playful",
                ),
            ],
            npc_will_leave=False,
        )

    menu = generate_follow_up_menu(state, result, exchange, 0, contextual_options)

    assert sum(option.category == "exit" for option in menu.options) == 1


def test_contextual_bespoke_accepts_specific_longer_labels() -> None:
    """Specific labels may need a few words for concrete context."""
    bespoke = ContextualBespoke(
        options=[
            FollowUpOption(
                label="Invite him to share his real feelings",
                category="deep",
                intent_kind="go_deeper",
                stat_used="eq",
                risk="medium",
                tone="curious",
            )
        ],
        npc_will_leave=False,
    )

    validate_contextual_bespoke(bespoke, [])


def test_follow_up_menu_accepts_specific_longer_labels() -> None:
    menu = mock_follow_up_menu().model_copy(
        update={
            "options": [
                FollowUpOption(
                    label="Ask if she really wants kids soon",
                    category="deep",
                    intent_kind="go_deeper",
                    stat_used="eq",
                    risk="medium",
                    tone="curious",
                ),
                FollowUpOption(
                    label="End on a good note",
                    category="exit",
                    intent_kind="end_softly",
                    stat_used="loyalty",
                    risk="safe",
                    tone="warm",
                ),
            ]
        }
    )

    validate_follow_up_menu(menu)


def test_explored_threads_only_includes_memories_about_the_target() -> None:
    """Cross-conversation topic memory: the context surfaces topics the player
    has already explored with *this* NPC (so the agent can avoid re-opening
    them), and excludes memories about other heartbreakers."""
    state = new_game(1)
    state.player.memories.extend(
        [
            Memory(
                id="m1",
                holder_id="player",
                subject_id="chloe",
                content="I learned Chloe wants kids before she turns thirty.",
                source="direct",
                formed_on_day=1,
                formed_on_turn=2,
                emotional_weight=6,
                tags=["deep", "talked_about_future"],
                recap_disposition=RecapDisposition.YOUR_DAY,
            ),
            Memory(
                id="m2",
                holder_id="player",
                subject_id="maya",
                content="Maya teased me about my dancing.",
                source="direct",
                formed_on_day=1,
                formed_on_turn=3,
                emotional_weight=4,
                tags=["banter"],
                recap_disposition=RecapDisposition.YOUR_DAY,
            ),
        ]
    )
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        success=True,
        relationship_deltas={"chloe": RelationshipDelta(affection=2)},
        tags=["friendly"],
    )
    exchange = Exchange(
        player_dialogue="Hey, good to see you.",
        npc_dialogue="You too.",
        npc_tone="warm",
        npc_mood_after=Mood.CONTENT,
    )

    ctx = contextual_options_context(state, result, exchange, 10, already_present=[])

    assert "wants kids before she turns thirty" in ctx.explored_threads
    assert "Maya teased" not in ctx.explored_threads


def test_explored_threads_defaults_when_no_prior_memories() -> None:
    """A brand-new connection reports fresh ground rather than an empty blob."""
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        success=True,
        relationship_deltas={"chloe": RelationshipDelta(affection=2)},
        tags=["friendly"],
    )
    exchange = Exchange(
        player_dialogue="Hi.",
        npc_dialogue="Hey.",
        npc_tone="warm",
        npc_mood_after=Mood.CONTENT,
    )

    ctx = contextual_options_context(state, result, exchange, 10, already_present=[])

    assert "fresh ground" in ctx.explored_threads


def test_context_includes_engine_option_labels_and_purposes() -> None:
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        success=True,
        relationship_deltas={"chloe": RelationshipDelta(affection=2)},
        tags=["friendly"],
    )
    exchange = Exchange(
        player_dialogue="How are you settling in?",
        npc_dialogue="I am still finding my feet.",
        npc_tone="warm",
        npc_mood_after=Mood.CONTENT,
    )
    existing = FollowUpOption(
        label="Ask something real",
        category="deep",
        intent_kind="go_deeper",
        stat_used="eq",
        risk="medium",
        tone="vulnerable",
    )

    ctx = contextual_options_context(
        state,
        result,
        exchange,
        10,
        already_present=[existing],
    )

    assert ctx.already_present[0].label == "Ask something real"
    assert ctx.already_present[0].category == "deep"
    assert ctx.already_present[0].intent_kind == "go_deeper"


def test_context_marks_the_conversation_left_for_a_private_chat() -> None:
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="maya",
            intent_id="flirty_intimate_eye_contact",
        ),
        success=True,
        private_chat_attempt=PrivateChatAttempt(
            target_id="maya",
            started_from_location="pool",
            success=True,
            chance=80,
            roll=20,
            blocked_participants=["maya", "liam"],
            blocked_topic="the early couples",
        ),
    )
    exchange = Exchange(
        player_dialogue="I wanted a minute with you.",
        npc_dialogue="Poor Liam. Fine, you have my attention.",
        npc_tone="flirty",
        npc_mood_after=Mood.FLIRTY,
    )

    ctx = contextual_options_context(state, result, exchange, 10, already_present=[])

    assert "away from Liam" in ctx.private_chat_context
    assert "do not return" in ctx.private_chat_context


def test_accepted_interruption_closes_previous_subject_for_options() -> None:
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.RESPOND_WITH,
            target_id="liam",
            intent_id="accept_interruption",
        ),
        success=True,
        relationship_deltas={
            "chloe": RelationshipDelta(affection=-2),
            "liam": RelationshipDelta(affection=3),
        },
    )
    exchange = Exchange(
        player_dialogue="Go on, Liam. What did you need?",
        npc_dialogue="Sorry for cutting in while you were talking with Chloe. Can we chat?",
        npc_tone="warm",
        npc_mood_after=Mood.CONTENT,
    )

    context = contextual_options_context(state, result, exchange, 0, already_present=[])

    assert context.closed_conversation_names == ["Chloe"]
    with pytest.raises(ValueError, match="closed conversation with Chloe"):
        validate_contextual_bespoke(
            ContextualBespoke(
                options=[
                    FollowUpOption(
                        label="Ask what Chloe was saying",
                        category="friendly",
                        intent_kind="change_subject",
                        stat_used="charm",
                        risk="safe",
                        tone="curious",
                    )
                ],
                npc_will_leave=False,
            ),
            [],
            forbidden_subject_names=context.closed_conversation_names,
        )


@pytest.mark.llm
def test_contextual_options_labels_are_specific() -> None:
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        success=True,
        relationship_deltas={"chloe": RelationshipDelta(affection=2)},
        tags=["friendly"],
    )
    exchange = Exchange(
        player_dialogue="What made you want to come here?",
        npc_dialogue=(
            "Teaching in Liverpool made me realize I keep helping everyone else grow up, "
            "but I never ask what I want for myself."
        ),
        npc_tone="vulnerable",
        npc_mood_after=Mood.CONTENT,
    )

    bespoke = ContextualOptionsAgent().generate(state, result, exchange, 20, [])
    generic = {
        "ask something deeper",
        "tell a joke",
        "keep flirting",
        "change the subject",
        "make a joke",
    }

    assert all(option.label.lower() not in generic for option in bespoke.options)
