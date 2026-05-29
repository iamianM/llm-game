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
        reveal_tier=3,
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
        reveal_tier=3,
    ),
    "ask_about_topic": FollowUpOption(
        label="Ask about that",
        category="friendly",
        intent_kind="ask_about_topic",
        stat_used="eq",
        risk="low",
        tone="curious",
        reveal_tier=1,
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
        reveal_tier=1,
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
        reveal_tier=2,
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
    intent_tags = set(result.tags or [])
    deep_intent = "deep" in intent_tags or "vulnerable" in intent_tags
    flirty_intent = "flirty" in intent_tags or "flirt" in intent_tags
    # On a missed deep beat: lead with honest_vulnerable (recovery on-topic)
    # before the defensive fallbacks, so the player sees a path forward
    # that continues the thread, not only "apologize / defend".
    if not result.success and deep_intent:
        options.append(_template("honest_vulnerable"))
    # On a missed flirt: offer a flirty recovery so the menu still has a
    # forward-on-topic option, not only defensive fallbacks. Use
    # deflect_with_humor (playful self-recovery) plus a re-escalate when the
    # gender pairing supports it.
    if not result.success and flirty_intent:
        options.append(_template("deflect_with_humor"))
        if _flirty_allowed(state, target.id):
            options.append(_template("escalate_flirt"))
    if not result.success or exchange.npc_tone in {"cold", "defensive", "suspicious"}:
        options.extend([_template("apologize"), _template("defend_self")])
    if result.success and target.relationship.affection >= 25:
        options.append(_template("go_deeper"))
        if _flirty_allowed(state, target.id):
            options.append(_template("escalate_flirt"))
            # When escalation is being offered on a flirty beat, also offer a
            # graceful pull-back so the menu isn't escalator-only. Relabel the
            # supportive_listen template here so the player reads it as a
            # genuine "cool the heat" choice instead of generic "Just listen".
            if exchange.npc_tone in {"flirty", "playful"}:
                pull_back = _template("supportive_listen").model_copy(
                    update={"label": "Cool the heat — slow it down"}
                )
                options.append(pull_back)
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
    # Defaults first guarantee an exit option exists; bespoke options come
    # second so they survive the cap over generic tone reactions. Dedupe by
    # intent_kind keeps the first occurrence, so a bespoke option that shares
    # an intent_kind with a default keeps the default's label — which is fine
    # because default labels are stable. The cap then preserves bespoke
    # specifics that fill an otherwise-empty beat (pull-back, on-topic gossip).
    base_defaults = default_options(state, result, exchange)
    tone_options = tone_reaction_options(state, exchange)
    # When the bespoke options already provide a specific on-topic deeper
    # push, suppress the generic "Ask something real" default — the bespoke
    # label ("Ask if she wants kids", "Ask why Cardiff") is concretely more
    # playable, and stacking them clutters the menu. Filter both defaults
    # and tone reactions because tone_reactions can also surface go_deeper.
    bespoke_kinds = {opt.intent_kind for opt in bespoke_options}
    if bespoke_kinds & {"go_deeper", "ask_about_topic", "honest_vulnerable"}:
        base_defaults = [opt for opt in base_defaults if opt.intent_kind != "go_deeper"]
        tone_options = [opt for opt in tone_options if opt.intent_kind != "go_deeper"]
    options = [
        *base_defaults,
        *bespoke_options,
        *tone_options,
    ]
    assembled = [
        _with_audience_hint(_with_reveal_default(option))
        for option in _cap_with_single_exit(_avoid_recent_repeats(state, _dedupe(options)), max_total=5)
    ]
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
    return _with_audience_hint(OPTION_TEMPLATES[intent_kind].model_copy(deep=True))


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


def _avoid_recent_repeats(state: GameState, options: list[FollowUpOption]) -> list[FollowUpOption]:
    conversation = state.active_conversation
    if conversation is None:
        return options
    recent_intents = {record.intent_id for record in conversation.exchanges[-2:]}
    if not recent_intents:
        return options
    fresh = [
        option
        for option in options
        if option.category == "exit" or option.intent_kind not in recent_intents
    ]
    if any(option.category != "exit" for option in fresh):
        return fresh
    fallback = _first_unused_template(recent_intents, {option.intent_kind for option in fresh})
    if fallback is not None:
        fresh.insert(0, fallback)
    return fresh


_FALLBACK_INTENTS: tuple[str, ...] = (
    "ask_about_topic",
    "change_subject",
    "joke_back",
    "go_deeper",
)


def _first_unused_template(recent: set[str], present: set[str]) -> FollowUpOption | None:
    for intent_kind in _FALLBACK_INTENTS:
        if intent_kind in recent or intent_kind in present:
            continue
        if intent_kind in OPTION_TEMPLATES:
            return _template(intent_kind)
    return None


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
    """Return the most recent memory the player can share as gossip with target.

    Eligibility is a *positive allowlist*, not a blacklist of known-bad system
    tags. A memory is shareable interpersonal gossip only when both hold:

    1. Its ``subject_id`` resolves to a real cast islander — never the player,
       the current listener, or a non-cast pseudo-subject like ``"villa"`` /
       ``"producers"``. This alone drops ceremony bookkeeping recorded against
       the villa.
    2. It is explicitly flagged ``gossip``. Ceremony / producer / system
       memories are "witnessed" villa events that carry their own kind tags
       (``ceremony``, ``elimination``, ``gather_scheduled``, ...) and never the
       ``gossip`` flag, so they fall outside the allowlist automatically —
       *including future system event kinds nobody remembered to blacklist*.

    Sharing one would otherwise surface raw engine tokens and invite the voice
    model to name absent cast, which reads as nonsense and can dead-screen the
    turn via the leak guard. A missed piece of real gossip (false negative) is
    a far safer failure than leaking an engine token (false positive), so the
    allowlist is deliberately conservative.
    """
    shareable_subjects = _cast_ids(state) - {"player", target_id}
    already_shared = _gossip_shared_with(state, target_id)
    for memory in reversed(state.player.memories):
        if memory.subject_id not in shareable_subjects:
            continue
        if memory.emotional_weight < 4:
            continue
        if "gossip" not in memory.tags:
            continue
        if memory.id in already_shared:
            # Don't re-offer gossip the player has already told this person.
            # Otherwise the same memory loops in the menu forever and the NPC
            # reacts as if hearing it fresh each time; suppressing it lets the
            # next-most-recent piece of gossip surface instead.
            continue
        return memory
    return None


def _cast_ids(state: GameState) -> set[str]:
    """Return every real islander id (eliminated or not).

    Membership here is the structural gate that keeps non-cast subjects
    (``"villa"`` and other engine pseudo-subjects) out of shareable gossip.
    """
    return {islander.id for islander in state.islanders}


def _gossip_shared_with(state: GameState, target_id: str) -> set[str]:
    """Source-memory ids the player has already shared with this target.

    ``apply_share_gossip_follow_up`` records a memory on the target tagged
    ``source_memory:<id>`` (with ``source_id == "player"``) whenever the player
    shares gossip, so repeats can be detected without any extra schema.
    """
    prefix = "source_memory:"
    for islander in state.islanders:
        if islander.id != target_id:
            continue
        return {
            tag.removeprefix(prefix)
            for memory in islander.memories
            if memory.source_id == "player"
            for tag in memory.tags
            if tag.startswith(prefix)
        }
    return set()


def _subject_name(state: GameState, memory: Memory) -> str:
    for islander in state.islanders:
        if islander.id == memory.subject_id:
            return islander.name
    return "Villa"


def _with_audience_hint(option: FollowUpOption) -> FollowUpOption:
    if option.audience_hint:
        return option
    positive = {
        "honest_vulnerable",
        "supportive_listen",
        "supportive_comfort",
        "supportive_reassure",
        "supportive_validate",
        "apologize",
        "end_softly",
    }
    negative = {"walk_away", "defend_self", "escalate_flirt"}
    if option.intent_kind.startswith("share_gossip:"):
        return option.model_copy(update={"audience_hint": "-"})
    if option.intent_kind.startswith("ask_gossip:"):
        return option.model_copy(update={"audience_hint": ""})
    if option.intent_kind in positive:
        return option.model_copy(update={"audience_hint": "+"})
    if option.intent_kind in negative and option.risk in {"medium", "high"}:
        return option.model_copy(update={"audience_hint": "-"})
    return option


def _with_reveal_default(option: FollowUpOption) -> FollowUpOption:
    if option.reveal_tier > 0 or option.category == "exit":
        return option
    if option.category == "deep" and option.risk != "safe":
        return option.model_copy(update={"reveal_tier": 3})
    if option.category == "friendly" and option.risk != "safe":
        return option.model_copy(update={"reveal_tier": 1})
    if option.category == "supportive" and option.risk not in {"safe", None}:
        return option.model_copy(update={"reveal_tier": 2})
    return option
