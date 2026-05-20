"""Tests for deterministic follow-up wheel defaults."""

from __future__ import annotations

from src.game.agents.contextual_options import ContextualBespoke
from src.game.agents.islander_voice import Exchange
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.follow_up_menu import generate_follow_up_menu
from src.game.engine.memory import add_memory, create_memory
from src.game.engine.option_defaults import (
    assemble_follow_up_menu,
    default_options,
    tone_reaction_options,
)
from src.game.engine.rules import MechanicalResult
from src.game.state.models import (
    Conversation,
    FollowUpOption,
    Gender,
    Mood,
    RelationshipDelta,
    new_game,
)


def test_default_options_always_include_one_exit() -> None:
    state, result, exchange = _context(success=True, tone="warm")

    options = default_options(state, result, exchange)

    assert sum(option.category == "exit" for option in options) == 1


def test_default_options_include_apologize_after_miss() -> None:
    state, result, exchange = _context(success=False, tone="defensive")

    options = default_options(state, result, exchange)

    assert "apologize" in {option.intent_kind for option in options}


def test_default_options_include_escalate_at_high_affection_opposite_sex() -> None:
    state, result, exchange = _context(success=True, tone="flirty")
    state.islanders[0].relationship.affection = 30

    options = default_options(state, result, exchange)

    assert "escalate_flirt" in {option.intent_kind for option in options}


def test_default_options_respect_gender_pair_filter() -> None:
    state, result, exchange = _context(success=True, tone="flirty")
    state.player.gender = state.islanders[0].gender
    state.islanders[0].relationship.affection = 40

    options = default_options(state, result, exchange)

    assert "escalate_flirt" not in {option.intent_kind for option in options}


def test_default_options_include_share_gossip_when_player_holds_memory() -> None:
    state, result, exchange = _context(success=True, tone="warm")
    add_memory(
        state,
        create_memory(
            holder_id="player",
            subject_id="maya",
            source="witnessed",
            day=1,
            turn=1,
            weight=7,
            tags=["gossip"],
            content="Maya looked rattled after Liam pulled away.",
        ),
    )

    options = default_options(state, result, exchange)

    assert any(option.intent_kind.startswith("share_gossip:") for option in options)


def test_tone_reaction_includes_escalate_for_flirty() -> None:
    state, _result, exchange = _context(success=True, tone="flirty")
    state.player.gender = Gender.MAN
    state.islanders[0].gender = Gender.WOMAN
    state.active_conversation = Conversation(target_id="chloe", started_on_turn=1, started_on_day=1)

    options = tone_reaction_options(state, exchange)

    assert "escalate_flirt" in {option.intent_kind for option in options}


def test_assemble_dedupes_and_caps_with_one_exit() -> None:
    state, result, exchange = _context(success=True, tone="warm")
    state.islanders[0].relationship.affection = 40
    bespoke = [
        FollowUpOption(
            label="Ask about Liverpool",
            category="deep",
            intent_kind="honest_vulnerable",
            stat_used="eq",
            risk="medium",
            tone="curious",
        ),
        FollowUpOption(
            label="Bring up Maya",
            category="gossip",
            intent_kind="ask_about_topic",
            stat_used="eq",
            risk="medium",
            tone="curious",
        ),
    ]

    menu = assemble_follow_up_menu(
        state,
        result,
        exchange,
        bespoke,
        npc_will_leave=False,
        npc_exit_line=None,
    )

    assert len(menu.options) <= 5
    assert sum(option.category == "exit" for option in menu.options) == 1
    assert len({option.intent_kind for option in menu.options}) == len(menu.options)


def test_assemble_avoids_recent_repeated_intents() -> None:
    state, result, exchange = _context(success=False, tone="defensive")
    state.active_conversation = Conversation(
        target_id="chloe",
        started_on_turn=1,
        started_on_day=1,
        exchanges=[
            _exchange_record("apologize"),
            _exchange_record("defend_self"),
        ],
    )

    menu = assemble_follow_up_menu(
        state,
        result,
        exchange,
        bespoke_options=[],
        npc_will_leave=False,
        npc_exit_line=None,
    )

    intents = {option.intent_kind for option in menu.options}
    assert "apologize" not in intents
    assert "defend_self" not in intents
    assert sum(option.category == "exit" for option in menu.options) == 1


def test_generate_follow_up_menu_uses_bespoke_and_defaults() -> None:
    state, result, exchange = _context(success=True, tone="warm")

    def contextual_options(*_args, **_kwargs) -> ContextualBespoke:
        return ContextualBespoke(
            options=[
                FollowUpOption(
                    label="Ask about Liverpool",
                    category="deep",
                    intent_kind="honest_vulnerable",
                    stat_used="eq",
                    risk="medium",
                    tone="curious",
                )
            ],
            npc_will_leave=False,
        )

    menu = generate_follow_up_menu(state, result, exchange, 20, contextual_options)

    assert any(option.label == "Ask about Liverpool" for option in menu.options)
    assert sum(option.category == "exit" for option in menu.options) == 1


def _context(*, success: bool, tone: str):
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_villa",
        ),
        success=success,
        relationship_deltas={"chloe": RelationshipDelta(affection=2)},
        tags=["friendly"],
    )
    exchange = Exchange(
        player_dialogue="What made you want to come here?",
        npc_dialogue="Teaching in Liverpool made me think about what I want.",
        npc_tone=tone,
        npc_mood_after=Mood.CONTENT,
    )
    return state, result, exchange


def _exchange_record(intent_id: str):
    from src.game.state.models import ExchangeRecord

    return ExchangeRecord(
        turn_index=1,
        intent_id=intent_id,
        player_dialogue="I am trying to be honest.",
        npc_dialogue="I hear that.",
        npc_tone="warm",
        npc_mood_after=Mood.CONTENT,
        success=True,
        tags=[intent_id],
        relationship_deltas={},
    )
