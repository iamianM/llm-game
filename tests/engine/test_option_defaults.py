"""Tests for deterministic follow-up wheel defaults."""

from __future__ import annotations

from src.game.agents.contextual_options import ContextualBespoke
from src.game.agents.heartbreaker_voice import Exchange
from src.game.agents.runtime import AgentValidationError
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.follow_up_menu import generate_follow_up_menu
from src.game.engine.memory import add_memory, add_memory_batch, create_memory
from src.game.engine.option_defaults import (
    assemble_follow_up_menu,
    default_options,
    tone_reaction_options,
)
from src.game.engine.rules import MechanicalResult
from src.game.state.memory import GossipSeed, MemoryBatch, MemoryDraft
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
    state.heartbreakers[0].relationship.affection = 30

    options = default_options(state, result, exchange)

    assert "escalate_flirt" in {option.intent_kind for option in options}


def test_default_options_respect_gender_pair_filter() -> None:
    state, result, exchange = _context(success=True, tone="flirty")
    state.player.gender = state.heartbreakers[0].gender
    state.heartbreakers[0].relationship.affection = 40

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
            content="Maya looked rattled after Liam stepped back.",
        ),
    )

    options = default_options(state, result, exchange)

    assert any(option.intent_kind.startswith("share_gossip:") for option in options)


def test_ceremony_memory_not_offered_as_share_gossip() -> None:
    """Ceremony / producer / system bookkeeping memories are 'witnessed' resort
    events but are not interpersonal gossip; offering them surfaces raw internal
    tokens and can dead-screen the voice agent, so they must be filtered out."""
    state, result, exchange = _context(success=True, tone="warm")
    state.player.memories.clear()
    add_memory(
        state,
        create_memory(
            holder_id="player",
            subject_id="resort",
            source="witnessed",
            day=1,
            turn=1,
            weight=5,
            tags=["ceremony", "gather_scheduled"],
            content="Everyone is called to the flame_deck for group_date_invite.",
        ),
    )

    options = default_options(state, result, exchange)

    assert all(not option.intent_kind.startswith("share_gossip:") for option in options)


def test_real_subject_ceremony_memory_not_offered_without_gossip_flag() -> None:
    """The eligibility check is a positive allowlist, not a tag blacklist: a
    witnessed ceremony memory about a *real cast member* (so it survives subject
    resolution) is still excluded because it lacks the ``gossip`` flag. This is
    the case a tag blacklist would miss whenever a new ceremony kind ships with
    a tag nobody remembered to deny-list."""
    state, result, exchange = _context(success=True, tone="warm")
    state.player.memories.clear()
    add_memory(
        state,
        create_memory(
            holder_id="player",
            subject_id="maya",
            source="witnessed",
            day=1,
            turn=1,
            weight=7,
            # A brand-new ceremony kind the blacklist never heard of.
            tags=["surprise_heart_out", "ceremony"],
            content="Maya was sent home in a shock heart_out.",
        ),
    )

    options = default_options(state, result, exchange)

    assert all(not option.intent_kind.startswith("share_gossip:") for option in options)


def test_witnessed_memory_offered_when_flagged_gossip() -> None:
    """No regression: a witnessed observation of two other heartbreakers that the
    curator flagged ``gossip`` is still offered as shareable gossip."""
    state, result, exchange = _context(success=True, tone="warm")
    state.player.memories.clear()
    add_memory(
        state,
        create_memory(
            holder_id="player",
            subject_id="maya",
            source="witnessed",
            day=1,
            turn=1,
            weight=5,
            tags=["background", "witnessed", "gossip"],
            content="I noticed Maya and Liam looked wrapped up in each other.",
        ),
    )

    options = default_options(state, result, exchange)

    assert any(option.intent_kind.startswith("share_gossip:") for option in options)


def test_direct_gossip_respects_curator_spreadable_targets() -> None:
    state, result, exchange = _context(success=True, tone="warm")
    state.player.memories.clear()
    add_memory_batch(
        state,
        MemoryBatch(
            memories=[
                MemoryDraft(
                    holder_id="player",
                    subject_id="maya",
                    source="direct",
                    emotional_weight=6,
                    tags=["gossip"],
                    content="Maya admitted the pressure was getting to her.",
                ),
                MemoryDraft(
                    holder_id="chloe",
                    subject_id="player",
                    source="direct",
                    emotional_weight=4,
                    tags=["supportive"],
                    content="The player listened carefully.",
                ),
            ],
            gossip_seeds=[
                GossipSeed(
                    holder_id="player",
                    subject_id="maya",
                    gist="Maya admitted the pressure was getting to her.",
                    spreadable_to=["jordan"],
                    emotional_weight=6,
                )
            ],
        ),
        day=1,
        turn=1,
    )

    chloe_options = default_options(state, result, exchange)
    assert all(not option.intent_kind.startswith("share_gossip:") for option in chloe_options)

    jordan_result = result.model_copy(
        update={"action": result.action.model_copy(update={"target_id": "jordan"})}
    )
    jordan_options = default_options(state, jordan_result, exchange)
    assert any(option.intent_kind.startswith("share_gossip:") for option in jordan_options)


def test_share_gossip_suppressed_after_already_shared_with_target() -> None:
    state, result, exchange = _context(success=True, tone="warm")
    state.player.memories.clear()
    first = create_memory(
        holder_id="player",
        subject_id="maya",
        source="witnessed",
        day=1,
        turn=1,
        weight=7,
        tags=["gossip"],
        content="Maya looked rattled after Liam stepped back.",
    )
    add_memory(state, first)

    before = default_options(state, result, exchange)
    assert any(option.intent_kind == f"share_gossip:{first.id}" for option in before)

    # Record that the player already told chloe this exact memory, exactly as
    # apply_share_gossip_follow_up would. It must no longer be offered.
    add_memory(
        state,
        create_memory(
            holder_id="chloe",
            subject_id="maya",
            source="told_by",
            source_id="player",
            day=1,
            turn=2,
            weight=7,
            tags=["gossip", f"source_memory:{first.id}"],
            content="Maya looked rattled after Liam stepped back.",
        ),
    )

    after = default_options(state, result, exchange)
    assert all(not option.intent_kind.startswith("share_gossip:") for option in after)


def test_share_gossip_surfaces_next_memory_after_one_shared() -> None:
    state, result, exchange = _context(success=True, tone="warm")
    state.player.memories.clear()
    older = create_memory(
        holder_id="player",
        subject_id="maya",
        source="witnessed",
        day=1,
        turn=1,
        weight=7,
        tags=["gossip"],
        content="Maya looked rattled after Liam stepped back.",
    )
    newer = create_memory(
        holder_id="player",
        subject_id="liam",
        source="witnessed",
        day=1,
        turn=3,
        weight=7,
        tags=["gossip"],
        content="Liam went quiet after the challenge.",
    )
    add_memory(state, older)
    add_memory(state, newer)

    first_offer = next(
        option for option in default_options(state, result, exchange)
        if option.intent_kind.startswith("share_gossip:")
    )
    assert first_offer.intent_kind == f"share_gossip:{newer.id}"

    add_memory(
        state,
        create_memory(
            holder_id="chloe",
            subject_id="liam",
            source="told_by",
            source_id="player",
            day=1,
            turn=4,
            weight=7,
            tags=["gossip", f"source_memory:{newer.id}"],
            content="Liam went quiet after the challenge.",
        ),
    )

    second_offer = next(
        option for option in default_options(state, result, exchange)
        if option.intent_kind.startswith("share_gossip:")
    )
    assert second_offer.intent_kind == f"share_gossip:{older.id}"


def test_tone_reaction_includes_escalate_for_flirty() -> None:
    state, _result, exchange = _context(success=True, tone="flirty")
    state.player.gender = Gender.MAN
    state.heartbreakers[0].gender = Gender.WOMAN
    state.active_conversation = Conversation(target_id="chloe", started_on_turn=1, started_on_day=1)

    options = tone_reaction_options(state, exchange)

    assert "escalate_flirt" in {option.intent_kind for option in options}


def test_assemble_dedupes_and_caps_with_one_exit() -> None:
    state, result, exchange = _context(success=True, tone="warm")
    state.heartbreakers[0].relationship.affection = 40
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


def test_assemble_fallback_skips_intents_already_in_recent_repeats() -> None:
    state, result, exchange = _context(success=True, tone="warm")
    state.active_conversation = Conversation(
        target_id="chloe",
        started_on_turn=1,
        started_on_day=1,
        exchanges=[
            _exchange_record("ask_about_topic"),
            _exchange_record("go_deeper"),
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
    assert "ask_about_topic" not in intents
    assert "go_deeper" not in intents
    assert sum(option.category != "exit" for option in menu.options) >= 1


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


def test_generate_follow_up_menu_survives_agent_raise() -> None:
    """The bespoke agent giving up (its live 3-retry exhaustion) must not dead-screen
    the turn after the NPC has already spoken — the wheel falls back to engine
    defaults so the player always keeps a usable, valid set of options."""
    state, result, exchange = _context(success=True, tone="warm")

    def boom(*_args, **_kwargs) -> ContextualBespoke:
        raise AgentValidationError("contextual options exhausted retries")

    menu = generate_follow_up_menu(state, result, exchange, 20, boom)

    assert sum(option.category == "exit" for option in menu.options) == 1
    assert any(option.category != "exit" for option in menu.options)
    # Default wheel keeps the NPC in the chat rather than silently ending it.
    assert menu.npc_will_leave is False


def test_generate_follow_up_menu_survives_invalid_agent_return() -> None:
    """An agent return the engine cannot assemble or validate (here: the wrong type)
    degrades to the default wheel rather than propagating the error up the turn."""
    state, result, exchange = _context(success=True, tone="warm")

    def garbage(*_args, **_kwargs):
        return "not a menu"

    menu = generate_follow_up_menu(state, result, exchange, 20, garbage)

    assert sum(option.category == "exit" for option in menu.options) == 1
    assert any(option.category != "exit" for option in menu.options)


def _context(*, success: bool, tone: str):
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
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
