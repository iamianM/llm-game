"""Deterministic gossip option injection for follow-up menus."""

from __future__ import annotations

from src.game.engine.gossip import gossip_subjects_for
from src.game.state.models import FollowUpMenu, FollowUpOption, GameState, Memory


def with_gossip_options(menu: FollowUpMenu, state: GameState) -> FollowUpMenu:
    """Add deterministic gossip options from memory offers or Known Facts."""
    conversation = state.active_conversation
    if conversation is None:
        return menu
    existing = {option.intent_kind for option in menu.options}
    if any(intent_kind.startswith("ask_gossip:") for intent_kind in existing):
        return menu
    target = next((islander for islander in state.islanders if islander.id == conversation.target_id), None)
    if target is None or target.relationship.affection < 25:
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
            label=f"Ask about {_islander_name(state, subject_id)}",
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
        replace_at = next(
            (index for index, existing_option in enumerate(options) if existing_option.category != "exit"),
            0,
        )
        options[replace_at] = option
    return menu.model_copy(update={"options": options})


def _subject_name(state: GameState, memory: Memory) -> str:
    return _islander_name(state, memory.subject_id)


def _islander_name(state: GameState, islander_id: str) -> str:
    for islander in state.islanders:
        if islander.id == islander_id:
            return islander.name
    return islander_id
