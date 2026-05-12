"""Interaction outcome calculation and relationship deltas.

Design sources:
- 02-Core-Mechanics.md: Interaction Success Formula, Relationship Stats
- 05-Interaction-System.md: Success Calculation Details, Relationship Application

Implementation rule:
All math lives here or in nearby deterministic engine modules. The Narrator
receives the resolved result; it never calculates outcomes.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field

from src.game.engine.actions import ActionKind, PlayerAction, validate_action
from src.game.engine.intents import Intent, available_intents_for, effective_risk, get_intent
from src.game.engine.memory import add_memory, create_memory
from src.game.engine.pull import PullAttempt
from src.game.state.models import (
    GameState,
    IslanderState,
    Location,
    RelationshipDelta,
    clamp_relationship,
)
from src.game.state.rng import SeededRng


class MechanicalResult(BaseModel):
    """Resolved mechanical outcome from one player action."""

    model_config = ConfigDict(extra="forbid")

    action: PlayerAction
    success: bool
    roll: int | None = None
    success_chance: int | None = None
    relationship_deltas: dict[str, RelationshipDelta] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    pull_attempt: PullAttempt | None = None


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

EXIT_INTENT_KINDS = {"end_softly", "walk_away", "change_subject_and_drift"}
INTERRUPTION_INTENT_KINDS = {
    "accept_interruption",
    "defer_interruption",
    "ignore_interruption",
}


def apply_action(state: GameState, action: PlayerAction, rng: SeededRng) -> MechanicalResult:
    """Apply one valid action and mutate ``state``."""
    validate_action(state, action)
    if action.kind is ActionKind.START_CONVERSATION:
        result = _apply_intent(state, action, rng)
        update_public_perception(state, action, result)
        return result
    if action.kind is ActionKind.RESPOND_WITH:
        result = _apply_follow_up(state, action, rng)
        update_public_perception(state, action, result)
        return result
    if action.kind is ActionKind.END_CONVERSATION:
        delta = RelationshipDelta()
        target_id: str | None = None
        if state.active_conversation is not None:
            target = _find_islander(state, state.active_conversation.target_id)
            target_id = target.id
            delta = RelationshipDelta(affection=-1)
            _apply_relationship_delta(target, delta)
        return MechanicalResult(
            action=action,
            success=True,
            relationship_deltas={} if target_id is None else {target_id: delta},
            tags=["walked_away"],
        )
    if action.kind is ActionKind.MOVE:
        return _apply_move(state, action)
    if action.kind is ActionKind.RECOUPLE:
        return MechanicalResult(action=action, success=True, tags=["recouple"])
    if action.kind is ActionKind.ADVANCE_PHASE:
        return MechanicalResult(action=action, success=True, tags=["phase"])
    raise ValueError(f"action is not implemented: {action.kind}")


def _apply_intent(state: GameState, action: PlayerAction, rng: SeededRng) -> MechanicalResult:
    target = _find_islander(state, action.target_id)
    if action.intent_id is None:
        raise ValueError("intent_id is required for conversation actions")
    intent = get_intent(action.intent_id)
    if intent not in available_intents_for(state, target.id):
        raise ValueError(f"intent is locked for target: {action.intent_id}")
    chance = intent_success_chance(state, target, intent)
    roll = rng.randint(1, 100)
    success = roll <= chance
    delta = (
        intent.relationship_deltas.success.model_copy()
        if success
        else intent.relationship_deltas.miss.model_copy()
    )
    _apply_relationship_delta(target, delta)
    return MechanicalResult(
        action=action,
        success=success,
        roll=roll,
        success_chance=chance,
        relationship_deltas={target.id: delta},
        tags=intent.tags,
    )


def _apply_relationship_delta(target: IslanderState, delta: RelationshipDelta) -> None:
    target.relationship.affection = clamp_relationship(
        target.relationship.affection + delta.affection
    )
    target.relationship.chemistry = clamp_relationship(
        target.relationship.chemistry + delta.chemistry
    )
    target.relationship.trust = clamp_relationship(target.relationship.trust + delta.trust)
    target.relationship.friendship = clamp_relationship(
        target.relationship.friendship + delta.friendship
    )


def _apply_follow_up(state: GameState, action: PlayerAction, rng: SeededRng) -> MechanicalResult:
    conversation = state.active_conversation
    if (
        conversation is not None
        and conversation.pending_interruption is not None
        and action.intent_id in INTERRUPTION_INTENT_KINDS
    ):
        return _apply_interruption_response(state, action, rng)
    if conversation is None or conversation.pending_options is None:
        raise ValueError("RESPOND_WITH requires active conversation pending options")
    option_index = _follow_up_option_index(state, action)
    option = conversation.pending_options.options[option_index]
    target = _find_islander(state, conversation.target_id)
    chance = follow_up_success_chance(state, target, option.stat_used, option.risk)
    roll = rng.randint(1, 100)
    success = roll <= chance
    if option.intent_kind.startswith("ask_gossip:"):
        delta = _apply_gossip_follow_up(state, conversation.target_id, option.intent_kind, success)
    else:
        delta = _follow_up_delta(option.intent_kind, option.risk, success)
    _apply_relationship_delta(target, delta)
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
        success_chance=chance,
        relationship_deltas={target.id: delta},
        tags=[option.intent_kind, option.risk, option.tone],
    )


def intent_success_chance(state: GameState, target: IslanderState, intent: Intent) -> int:
    """Calculate F1 intent success chance."""
    stat = getattr(state.player.stats, intent.stat_used)
    if not isinstance(stat, int):
        raise ValueError(f"unknown numeric stat for intent: {intent.stat_used}")
    mood_modifier = -10 if target.mood.value in {"upset", "angry"} else 0
    risk = effective_risk(intent)
    chance = (
        50
        + (stat * 5)
        + (target.relationship.affection // 4)
        + mood_modifier
        + RISK_SUCCESS_MODIFIER[risk]
    )
    return max(5, min(RISK_SUCCESS_CAP[risk], chance))


def follow_up_success_chance(
    state: GameState,
    target: IslanderState,
    stat_used: str | None,
    risk: str,
) -> int:
    """Calculate success chance for a freeform contextual follow-up."""
    stat = 5 if stat_used is None else getattr(state.player.stats, stat_used)
    if not isinstance(stat, int):
        raise ValueError(f"unknown numeric stat for follow-up: {stat_used}")
    risk_modifier = RISK_SUCCESS_MODIFIER[risk]
    chance = 50 + (stat * 5) + (target.relationship.affection // 5) + risk_modifier
    return max(5, min(RISK_SUCCESS_CAP[risk], chance))


def _apply_move(state: GameState, action: PlayerAction) -> MechanicalResult:
    if action.target_id is None:
        raise ValueError("target_id is required for MOVE")
    state.location_id = Location(action.target_id)
    return MechanicalResult(action=action, success=True, tags=["move"])


def _find_islander(state: GameState, target_id: str | None) -> IslanderState:
    if target_id is None:
        raise ValueError("target_id is required")
    for islander in state.islanders:
        if islander.id == target_id:
            return islander
    raise ValueError(f"unknown islander: {target_id}")


def _follow_up_option_index(state: GameState, action: PlayerAction) -> int:
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


def update_public_perception(
    state: GameState,
    action: PlayerAction,
    result: MechanicalResult,
) -> None:
    """Apply small deterministic public-perception movement."""
    delta = 0
    if "supportive" in result.tags and result.success:
        delta = 2
    elif "honest_vulnerable" in result.tags and result.success:
        delta = 1
    elif "escalate_flirt" in result.tags and not result.success:
        delta = -1
    elif "intense" in result.tags and not result.success:
        delta = -2
    elif "flirty" in result.tags and not result.success:
        delta = -1
    state.player.public_perception = clamp_relationship(state.player.public_perception + delta)


def _apply_gossip_follow_up(
    state: GameState,
    source_id: str,
    intent_kind: str,
    success: bool,
) -> RelationshipDelta:
    memory_id = intent_kind.removeprefix("ask_gossip:")
    conversation = state.active_conversation
    if conversation is None:
        raise ValueError("gossip follow-up requires active conversation")
    source_memory = next(
        (memory for memory in conversation.gossip_offers if memory.id == memory_id),
        None,
    )
    if source_memory is None:
        raise ValueError(f"gossip memory not offered: {memory_id}")
    if not success:
        return RelationshipDelta()
    add_memory(
        state,
        create_memory(
            holder_id="player",
            subject_id=source_memory.subject_id,
            source="told_by",
            source_id=source_id,
            day=state.day,
            turn=state.turn_index,
            weight=source_memory.emotional_weight,
            tags=["gossip", f"source_memory:{source_memory.id}", *source_memory.tags],
            content=source_memory.content,
        ),
    )
    return RelationshipDelta(trust=2)


def defer_chance(state: GameState, interrupter_id: str) -> int:
    """Return the chance that a polite deferral lands well."""
    interrupter = _find_islander(state, interrupter_id)
    chance = 50 + (state.player.stats.eq * 4) + (interrupter.relationship.affection // 4)
    return max(10, min(90, chance))


def _apply_interruption_response(
    state: GameState,
    action: PlayerAction,
    rng: SeededRng,
) -> MechanicalResult:
    conversation = state.active_conversation
    if conversation is None or conversation.pending_interruption is None:
        raise ValueError("interruption response requires a pending interruption")
    interruption = conversation.pending_interruption
    current = _find_islander(state, conversation.target_id)
    interrupter = _find_islander(state, interruption.interrupter_id)
    intent_id = action.intent_id
    deltas: dict[str, RelationshipDelta] = {}
    roll: int | None = None
    chance: int | None = None
    success = True
    tags = ["interruption", str(intent_id), interruption.reason, interruption.urgency]

    if intent_id == "accept_interruption":
        current_delta = RelationshipDelta(affection=-2)
        interrupter_delta = RelationshipDelta(affection=3)
        _apply_relationship_delta(current, current_delta)
        _apply_relationship_delta(interrupter, interrupter_delta)
        deltas = {current.id: current_delta, interrupter.id: interrupter_delta}
    elif intent_id == "defer_interruption":
        chance = defer_chance(state, interrupter.id)
        roll = rng.randint(1, 100)
        success = roll <= chance
        interrupter_delta = RelationshipDelta(affection=-1 if success else -3)
        _apply_relationship_delta(interrupter, interrupter_delta)
        deltas = {interrupter.id: interrupter_delta}
        if not success:
            _remember_interruption_snub(state, interrupter.id, "snubbed_publicly", 7)
    elif intent_id == "ignore_interruption":
        interrupter_delta = RelationshipDelta(affection=-4)
        _apply_relationship_delta(interrupter, interrupter_delta)
        deltas = {interrupter.id: interrupter_delta}
        _remember_interruption_snub(state, interrupter.id, "ignored_in_public", 8)
    else:
        raise ValueError(f"unknown interruption response: {intent_id}")

    conversation.pending_interruption = None
    return MechanicalResult(
        action=action.model_copy(update={"target_id": interrupter.id}),
        success=success,
        roll=roll,
        success_chance=chance,
        relationship_deltas=deltas,
        tags=tags,
    )


def _remember_interruption_snub(
    state: GameState,
    interrupter_id: str,
    tag: str,
    weight: int,
) -> None:
    add_memory(
        state,
        create_memory(
            holder_id=interrupter_id,
            subject_id="player",
            source="direct",
            day=state.day,
            turn=state.turn_index,
            weight=weight,
            tags=["interruption", tag],
            content=f"I remember the player leaving me feeling {tag.replace('_', ' ')}.",
        ),
    )
    for islander in state.islanders:
        if (
            islander.id != interrupter_id
            and not islander.eliminated
            and islander.location_id == state.location_id
        ):
            add_memory(
                state,
                create_memory(
                    holder_id=islander.id,
                    subject_id="player",
                    source="witnessed",
                    day=state.day,
                    turn=state.turn_index,
                    weight=max(4, weight - 2),
                    tags=["interruption", tag, "witnessed"],
                    content=f"I saw the player handle an interruption and leave someone {tag.replace('_', ' ')}.",
                ),
            )


def _follow_up_delta(intent_kind: str, risk: str, success: bool) -> RelationshipDelta:
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
