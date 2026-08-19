"""Auditable success-chance formulas."""

from __future__ import annotations

from src.game.engine.compatibility import compatibility_bonus, dealbreaker_penalty
from src.game.engine.intents import Intent, effective_risk
from src.game.engine.results import ChanceBreakdown
from src.game.state.models import GameState, HeartbreakerState

RISK_SUCCESS_CAP = {
    "safe": 90,
    "low": 80,
    "medium": 65,
    "high": 50,
}

RISK_SUCCESS_MODIFIER = {
    "safe": 15,
    "low": 5,
    "medium": -5,
    "high": -20,
}


def intent_success_chance(state: GameState, target: HeartbreakerState, intent: Intent) -> int:
    """Calculate F1 intent success chance."""
    return intent_success_breakdown(state, target, intent).final_chance


def intent_success_breakdown(
    state: GameState,
    target: HeartbreakerState,
    intent: Intent,
) -> ChanceBreakdown:
    """Calculate an auditable F1 intent success chance."""
    stat = getattr(state.player.stats, intent.stat_used)
    if not isinstance(stat, int):
        raise ValueError(f"unknown numeric stat for intent: {intent.stat_used}")
    mood_modifier = -10 if target.mood.value in {"upset", "angry"} else 0
    risk = effective_risk(intent)
    stat_contribution = stat * 5
    affection_contribution = target.relationship.affection // 4
    compat = compatibility_bonus(state, target, intent.tags)
    penalty = dealbreaker_penalty(target, intent.tags)
    pre_cap = (
        50
        + stat_contribution
        + affection_contribution
        + mood_modifier
        + RISK_SUCCESS_MODIFIER[risk]
        + compat
        - penalty
    )
    cap = RISK_SUCCESS_CAP[risk]
    return ChanceBreakdown(
        kind="initial_intent",
        base=50,
        stat_name=intent.stat_used,
        stat_value=stat,
        stat_multiplier=5,
        stat_contribution=stat_contribution,
        affection_value=target.relationship.affection,
        affection_divisor=4,
        affection_contribution=affection_contribution,
        risk=risk,
        risk_modifier=RISK_SUCCESS_MODIFIER[risk],
        mood_modifier=mood_modifier,
        compatibility_bonus=compat,
        dealbreaker_penalty=penalty,
        pre_cap=pre_cap,
        cap=cap,
        floor=5,
        final_chance=max(5, min(cap, pre_cap)),
    )


def follow_up_success_chance(
    state: GameState,
    target: HeartbreakerState,
    stat_used: str | None,
    risk: str,
) -> int:
    """Calculate success chance for a freeform contextual follow-up."""
    return follow_up_success_breakdown(state, target, stat_used, risk).final_chance


def follow_up_success_breakdown(
    state: GameState,
    target: HeartbreakerState,
    stat_used: str | None,
    risk: str,
) -> ChanceBreakdown:
    """Calculate an auditable freeform contextual follow-up success chance."""
    stat = 5 if stat_used is None else getattr(state.player.stats, stat_used)
    if not isinstance(stat, int):
        raise ValueError(f"unknown numeric stat for follow-up: {stat_used}")
    risk_modifier = RISK_SUCCESS_MODIFIER[risk]
    stat_contribution = stat * 5
    affection_contribution = target.relationship.affection // 5
    tags = [] if stat_used is None else [stat_used]
    compat = compatibility_bonus(state, target, tags)
    penalty = dealbreaker_penalty(target, tags)
    pre_cap = 50 + stat_contribution + affection_contribution + risk_modifier + compat - penalty
    cap = RISK_SUCCESS_CAP[risk]
    return ChanceBreakdown(
        kind="follow_up",
        base=50,
        stat_name=stat_used or "neutral",
        stat_value=stat,
        stat_multiplier=5,
        stat_contribution=stat_contribution,
        affection_value=target.relationship.affection,
        affection_divisor=5,
        affection_contribution=affection_contribution,
        risk=risk,
        risk_modifier=risk_modifier,
        compatibility_bonus=compat,
        dealbreaker_penalty=penalty,
        pre_cap=pre_cap,
        cap=cap,
        floor=5,
        final_chance=max(5, min(cap, pre_cap)),
    )
