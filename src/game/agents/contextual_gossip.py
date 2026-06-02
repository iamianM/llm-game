"""Deterministic gossip option injection for follow-up menus."""

from __future__ import annotations

from src.game.engine.gossip import gossip_subjects_for
from src.game.state.models import FollowUpMenu, FollowUpOption, GameState, Memory

_DEFLECTIVE_TONES = {"defensive", "cold", "suspicious", "anxious"}
_VULNERABLE_TONES = {"vulnerable"}


def with_gossip_options(menu: FollowUpMenu, state: GameState) -> FollowUpMenu:
    """Add deterministic gossip options from memory offers or Known Facts."""
    conversation = state.active_conversation
    if conversation is None:
        return menu
    existing = {option.intent_kind for option in menu.options}
    if any(intent_kind.startswith("ask_gossip:") for intent_kind in existing):
        return menu
    target = next((heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == conversation.target_id), None)
    if target is None or target.relationship.affection < 25:
        return menu
    # Do not inject a topic-switching gossip option when the last exchange
    # was vulnerable, deflective, or anxious — that beat needs on-topic
    # continuation, not a pivot to a third party.
    if conversation.exchanges:
        last_tone = (conversation.exchanges[-1].npc_tone or "").lower()
        if last_tone in _DEFLECTIVE_TONES or last_tone in _VULNERABLE_TONES:
            return menu
    options = list(menu.options)
    if conversation.gossip_offers:
        for memory in conversation.gossip_offers:
            option = _memory_gossip_option(state, memory)
            if option.intent_kind not in existing:
                return _insert_option(menu, options, option)
    for subject_id in gossip_subjects_for(state, conversation.target_id):
        intent_kind = f"ask_gossip:about_{subject_id}"
        if intent_kind in existing:
            continue
        option = FollowUpOption(
            label=f"Ask about {_heartbreaker_name(state, subject_id)}",
            category="gossip",
            intent_kind=intent_kind,
            stat_used="eq",
            risk="medium",
            tone="curious",
            reveal_tier=2,
        )
        return _insert_option(menu, options, option)
    return menu


def _memory_gossip_option(state: GameState, memory: Memory) -> FollowUpOption:
    return FollowUpOption(
        label=f"Ask about {_subject_name(state, memory)}",
        category="gossip",
        intent_kind=f"ask_gossip:{memory.id}",
        stat_used="eq",
        risk="medium",
        tone="curious",
    )


def _insert_option(menu: FollowUpMenu, options: list[FollowUpOption], option: FollowUpOption) -> FollowUpMenu:
    if len(options) < 5:
        options.insert(max(0, len(options) - 1), option)
    else:
        # When the menu is at cap, replace a low-value defensive option
        # (apologize / defend_self / change_subject) rather than a content
        # option that drives the conversation forward (deflect_with_humor /
        # joke_back / go_deeper / escalate_flirt / honest_vulnerable /
        # supportive_listen). Falling back to "first non-exit" used to delete
        # the menu's flirt recovery in favor of gossip on every Day-1 chat
        # that crossed the gossip threshold.
        _DROPPABLE = {"apologize", "defend_self", "change_subject"}
        replace_at = next(
            (i for i, existing in enumerate(options) if existing.intent_kind in _DROPPABLE),
            None,
        )
        if replace_at is None:
            replace_at = next(
                (i for i, existing in enumerate(options) if existing.category != "exit"),
                0,
            )
        options[replace_at] = option
    return menu.model_copy(update={"options": options})


def _subject_name(state: GameState, memory: Memory) -> str:
    return _heartbreaker_name(state, memory.subject_id)


def _heartbreaker_name(state: GameState, heartbreaker_id: str) -> str:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == heartbreaker_id:
            return heartbreaker.name
    return heartbreaker_id
