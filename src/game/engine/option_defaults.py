"""Deterministic follow-up option assembly."""

from __future__ import annotations

from src.game.agents.contextual_options import validate_follow_up_menu
from src.game.agents.islander_voice import Exchange
from src.game.engine.results import MechanicalResult
from src.game.state.models import FollowUpMenu, FollowUpOption, GameState, IslanderState, Memory

TONE_REACTIONS: dict[str, list[str]] = {
    "suspicious": ["defend_self", "honest_vulnerable", "change_subject"],
    "defensive": ["apologize", "change_subject", "end_softly"],
    "cold": ["apologize", "end_softly"],
    "vulnerable": ["go_deeper", "supportive_listen", "supportive_validate"],
    "flirty": ["escalate_flirt", "joke_back"],
    "warm": ["go_deeper", "joke_back", "ask_about_topic"],
    "playful": ["joke_back", "escalate_flirt", "deflect_with_humor"],
    "amused": ["joke_back", "ask_about_topic"],
}

OPTION_TEMPLATES: dict[str, FollowUpOption] = {
    "honest_vulnerable": FollowUpOption(
        label="Be honest back",
        category="deep",
        intent_kind="honest_vulnerable",
        stat_used="eq",
        risk="medium",
        tone="sincere",
    ),
    "escalate_flirt": FollowUpOption(
        label="Push the flirt",
        category="flirty",
        intent_kind="escalate_flirt",
        stat_used="graft",
        risk="high",
        tone="flirty",
    ),
    "deflect_with_humor": FollowUpOption(
        label="Deflect with humor",
        category="banter",
        intent_kind="deflect_with_humor",
        stat_used="banter",
        risk="medium",
        tone="playful",
    ),
    "joke_back": FollowUpOption(
        label="Tease them back",
        category="banter",
        intent_kind="joke_back",
        stat_used="banter",
        risk="low",
        tone="playful",
    ),
    "go_deeper": FollowUpOption(
        label="Ask something real",
        category="deep",
        intent_kind="go_deeper",
        stat_used="eq",
        risk="medium",
        tone="vulnerable",
    ),
    "ask_about_topic": FollowUpOption(
        label="Ask about that",
        category="friendly",
        intent_kind="ask_about_topic",
        stat_used="eq",
        risk="low",
        tone="curious",
    ),
    "apologize": FollowUpOption(
        label="Apologize honestly",
        category="supportive",
        intent_kind="apologize",
        stat_used="eq",
        risk="safe",
        tone="apologetic",
    ),
    "defend_self": FollowUpOption(
        label="Defend yourself",
        category="supportive",
        intent_kind="defend_self",
        stat_used="loyalty",
        risk="medium",
        tone="defensive",
    ),
    "change_subject": FollowUpOption(
        label="Change the subject",
        category="friendly",
        intent_kind="change_subject",
        stat_used="charm",
        risk="safe",
        tone="evasive",
    ),
    "supportive_listen": FollowUpOption(
        label="Just listen",
        category="supportive",
        intent_kind="supportive_listen",
        stat_used="eq",
        risk="safe",
        tone="warm",
    ),
    "supportive_validate": FollowUpOption(
        label="Validate their feelings",
        category="supportive",
        intent_kind="supportive_validate",
        stat_used="eq",
        risk="low",
        tone="warm",
    ),
    "end_softly": FollowUpOption(
        label="End on a good note",
        category="exit",
        intent_kind="end_softly",
        stat_used=None,
        risk="safe",
        tone="warm",
    ),
    "walk_away": FollowUpOption(
        label="Give them space",
        category="exit",
        intent_kind="walk_away",
        stat_used=None,
        risk="safe",
        tone="cool",
    ),
}


def default_options(state: GameState, result: MechanicalResult, exchange: Exchange) -> list[FollowUpOption]:
    """Return deterministic always-on options for the current beat."""
    target = _target(state, result)
    options = [_exit_option(exchange.npc_tone)]
    if not result.success or exchange.npc_tone in {"cold", "defensive", "suspicious"}:
        options.extend([_template("apologize"), _template("defend_self")])
    if result.success and target.relationship.affection >= 25:
        options.append(_template("go_deeper"))
        if _flirty_allowed(state, target.id):
            options.append(_template("escalate_flirt"))
    options.append(_template("joke_back"))
    gossip = _player_shareable_memory(state, target.id)
    if gossip is not None:
        options.append(
            FollowUpOption(
                label=f"Share {_subject_name(state, gossip)} gossip",
                category="gossip",
                intent_kind=f"share_gossip:{gossip.id}",
                stat_used="eq",
                risk="medium",
                tone="gossipy",
            )
        )
    return _dedupe(options)


def tone_reaction_options(state: GameState, exchange: Exchange) -> list[FollowUpOption]:
    """Return deterministic options keyed to the NPC's tone."""
    target_id = state.active_conversation.target_id if state.active_conversation else ""
    options: list[FollowUpOption] = []
    for intent_kind in TONE_REACTIONS.get(exchange.npc_tone, [])[:2]:
        if intent_kind == "escalate_flirt" and not _flirty_allowed(state, target_id):
            continue
        options.append(_template(intent_kind))
    return _dedupe(options)


def assemble_follow_up_menu(
    state: GameState,
    result: MechanicalResult,
    exchange: Exchange,
    bespoke_options: list[FollowUpOption],
    *,
    npc_will_leave: bool,
    npc_exit_line: str | None,
) -> FollowUpMenu:
    """Combine defaults, tone reactions, and bespoke options into one wheel."""
    options = [
        *default_options(state, result, exchange),
        *tone_reaction_options(state, exchange),
        *bespoke_options,
    ]
    assembled = _cap_with_single_exit(_dedupe(options), max_total=5)
    menu = FollowUpMenu(
        options=assembled,
        npc_will_leave=npc_will_leave,
        npc_exit_line=npc_exit_line,
    )
    validate_follow_up_menu(menu)
    return menu


def already_present_intents(
    state: GameState,
    result: MechanicalResult,
    exchange: Exchange,
) -> list[str]:
    """Return intent kinds already supplied by deterministic option builders."""
    return [
        option.intent_kind
        for option in _dedupe(
            [*default_options(state, result, exchange), *tone_reaction_options(state, exchange)]
        )
    ]


def _template(intent_kind: str) -> FollowUpOption:
    return OPTION_TEMPLATES[intent_kind].model_copy(deep=True)


def _exit_option(tone: str) -> FollowUpOption:
    if tone in {"cold", "defensive", "suspicious", "sharp"}:
        return _template("walk_away")
    return _template("end_softly")


def _dedupe(options: list[FollowUpOption]) -> list[FollowUpOption]:
    seen: set[str] = set()
    deduped: list[FollowUpOption] = []
    for option in options:
        if option.intent_kind in seen:
            continue
        seen.add(option.intent_kind)
        deduped.append(option)
    return deduped


def _cap_with_single_exit(options: list[FollowUpOption], *, max_total: int) -> list[FollowUpOption]:
    exit_options = [option for option in options if option.category == "exit"]
    exit_option = exit_options[0] if exit_options else _template("end_softly")
    non_exit = [option for option in options if option.category != "exit"]
    capped = non_exit[: max_total - 1]
    insert_at = min(len(capped), 2)
    capped.insert(insert_at, exit_option)
    if len(capped) < 2:
        capped.insert(0, _template("ask_about_topic"))
    return capped


def _target(state: GameState, result: MechanicalResult) -> IslanderState:
    target_id = result.action.target_id
    for islander in state.islanders:
        if islander.id == target_id:
            return islander
    raise ValueError(f"follow-up target not found: {target_id}")


def _flirty_allowed(state: GameState, target_id: str) -> bool:
    for islander in state.islanders:
        if islander.id == target_id:
            return islander.gender != state.player.gender
    return False


def _player_shareable_memory(state: GameState, target_id: str) -> Memory | None:
    for memory in reversed(state.player.memories):
        if memory.subject_id in {"player", target_id}:
            continue
        if memory.emotional_weight < 4:
            continue
        if "gossip" in memory.tags or memory.source in {"witnessed", "told_by"}:
            return memory
    return None


def _subject_name(state: GameState, memory: Memory) -> str:
    for islander in state.islanders:
        if islander.id == memory.subject_id:
            return islander.name
    return "Villa"
