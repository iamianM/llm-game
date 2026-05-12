"""Contextual follow-up mechanics."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict

from src.game.engine.actions import PlayerAction
from src.game.engine.chance import follow_up_success_breakdown
from src.game.engine.gossip import apply_gossip_follow_up
from src.game.engine.interruptions import (
    INTERRUPTION_INTENT_KINDS,
    apply_interruption_response,
)
from src.game.engine.results import MechanicalResult
from src.game.engine.state_access import apply_relationship_delta, find_islander
from src.game.state.models import GameState, RelationshipDelta
from src.game.state.rng import SeededRng


class FollowUpDeltaTable(BaseModel):
    """Success and miss deltas for one contextual follow-up intent."""

    model_config = ConfigDict(extra="forbid")

    success: RelationshipDelta
    miss: RelationshipDelta


FOLLOW_UP_DELTA_TABLE: dict[str, FollowUpDeltaTable] = {
    "honest_vulnerable": FollowUpDeltaTable(
        success=RelationshipDelta(trust=5, affection=2),
        miss=RelationshipDelta(trust=-2),
    ),
    "escalate_flirt": FollowUpDeltaTable(
        success=RelationshipDelta(chemistry=6, affection=1),
        miss=RelationshipDelta(chemistry=-3, trust=-1),
    ),
    "deflect_with_humor": FollowUpDeltaTable(
        success=RelationshipDelta(friendship=3, chemistry=1),
        miss=RelationshipDelta(),
    ),
    "joke_back": FollowUpDeltaTable(
        success=RelationshipDelta(friendship=2),
        miss=RelationshipDelta(friendship=-1),
    ),
    "go_deeper": FollowUpDeltaTable(
        success=RelationshipDelta(trust=4, affection=3),
        miss=RelationshipDelta(trust=-1),
    ),
    "ask_about_topic": FollowUpDeltaTable(
        success=RelationshipDelta(affection=2, trust=1),
        miss=RelationshipDelta(),
    ),
    "apologize": FollowUpDeltaTable(
        success=RelationshipDelta(trust=5),
        miss=RelationshipDelta(),
    ),
    "defend_self": FollowUpDeltaTable(
        success=RelationshipDelta(trust=2),
        miss=RelationshipDelta(trust=-2),
    ),
    "change_subject": FollowUpDeltaTable(
        success=RelationshipDelta(friendship=1),
        miss=RelationshipDelta(affection=-1),
    ),
    "end_softly": FollowUpDeltaTable(
        success=RelationshipDelta(trust=1),
        miss=RelationshipDelta(trust=1),
    ),
    "walk_away": FollowUpDeltaTable(
        success=RelationshipDelta(affection=-1),
        miss=RelationshipDelta(affection=-1),
    ),
    "change_subject_and_drift": FollowUpDeltaTable(
        success=RelationshipDelta(trust=1),
        miss=RelationshipDelta(trust=1),
    ),
}

RISK_DELTA_SCALE = {
    "safe": 0.0,
    "low": 0.75,
    "medium": 1.0,
    "high": 1.5,
}

EXIT_INTENT_KINDS = {"end_softly", "walk_away", "change_subject_and_drift"}


def apply_follow_up(state: GameState, action: PlayerAction, rng: SeededRng) -> MechanicalResult:
    """Apply one contextual follow-up or interruption response."""
    conversation = state.active_conversation
    if (
        conversation is not None
        and conversation.pending_interruption is not None
        and action.intent_id in INTERRUPTION_INTENT_KINDS
    ):
        return apply_interruption_response(state, action, rng)
    if conversation is None or conversation.pending_options is None:
        raise ValueError("RESPOND_WITH requires active conversation pending options")
    option_index = follow_up_option_index(state, action)
    option = conversation.pending_options.options[option_index]
    target = find_islander(state, conversation.target_id)
    breakdown = follow_up_success_breakdown(state, target, option.stat_used, option.risk)
    roll = rng.randint(1, 100)
    success = roll <= breakdown.final_chance
    if option.intent_kind.startswith("ask_gossip:"):
        delta = apply_gossip_follow_up(state, conversation.target_id, option.intent_kind, success)
    else:
        delta = follow_up_delta(option.intent_kind, option.risk, success)
    apply_relationship_delta(target, delta)
    normalized = action.model_copy(
        update={
            "target_id": target.id,
            "intent_id": option.intent_kind,
            "option_index": option_index,
        }
    )
    return MechanicalResult(
        action=normalized,
        success=success,
        roll=roll,
        success_chance=breakdown.final_chance,
        chance_breakdown=breakdown,
        relationship_deltas={target.id: delta},
        tags=[option.intent_kind, option.risk, option.tone],
    )


def follow_up_option_index(state: GameState, action: PlayerAction) -> int:
    """Resolve a follow-up action to the current menu index."""
    conversation = state.active_conversation
    if conversation is None or conversation.pending_options is None:
        raise ValueError("no pending options")
    if action.option_index is not None:
        return action.option_index
    if action.intent_id is None:
        raise ValueError("RESPOND_WITH requires option_index or intent_id")
    for index, option in enumerate(conversation.pending_options.options):
        if option.intent_kind == action.intent_id:
            return index
    raise ValueError(f"follow-up intent not found in pending menu: {action.intent_id}")


def follow_up_delta(intent_kind: str, risk: str, success: bool) -> RelationshipDelta:
    """Return scaled deltas for one contextual follow-up."""
    if intent_kind not in FOLLOW_UP_DELTA_TABLE:
        raise ValueError(f"unknown follow-up intent_kind: {intent_kind}")
    table = FOLLOW_UP_DELTA_TABLE[intent_kind]
    base = table.success if success else table.miss
    scale = 1.0 if intent_kind in EXIT_INTENT_KINDS else RISK_DELTA_SCALE[risk]
    return RelationshipDelta(
        affection=_scale_delta(base.affection, scale),
        chemistry=_scale_delta(base.chemistry, scale),
        trust=_scale_delta(base.trust, scale),
        friendship=_scale_delta(base.friendship, scale),
    )


def _scale_delta(value: int, scale: float) -> int:
    if value == 0 or scale == 0:
        return 0
    scaled = abs(value) * scale
    return int(math.copysign(math.floor(scaled + 0.5), value))
