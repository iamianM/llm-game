"""Top-level action dispatcher for deterministic game rules."""

from __future__ import annotations

from src.game.content.ambient import get_ambient_option
from src.game.engine.actions import ActionKind, PlayerAction, validate_action
from src.game.engine.casa_amor import apply_casa_decision
from src.game.engine.challenges import resolve_challenge
from src.game.engine.chance import (
    follow_up_success_breakdown,
    follow_up_success_chance,
    intent_success_breakdown,
    intent_success_chance,
)
from src.game.engine.character_creation import create_character
from src.game.engine.compatibility import apply_familiarity, attachment_delta_modifier
from src.game.engine.followups import (
    EXIT_INTENT_KINDS,
    FOLLOW_UP_DELTA_TABLE,
    apply_follow_up,
    follow_up_delta,
)
from src.game.engine.hideaway import HIDEAWAY_TAGS, apply_hideaway
from src.game.engine.intents import available_intents_for, get_intent
from src.game.engine.interruptions import (
    INTERRUPTION_INTENT_KINDS,
    apply_interruption_response,
    defer_chance,
    defer_chance_breakdown,
)
from src.game.engine.perception import update_public_perception
from src.game.engine.proposals import apply_npc_proposal_response, apply_player_proposal
from src.game.engine.results import ChanceBreakdown, MechanicalResult
from src.game.engine.state_access import apply_relationship_delta, find_islander
from src.game.state.casa import CasaDecision
from src.game.state.models import GameState, Gender, Location, PlayerStats, RelationshipDelta
from src.game.state.rng import SeededRng


def apply_action(state: GameState, action: PlayerAction, rng: SeededRng) -> MechanicalResult:
    """Apply one valid action and mutate ``state``."""
    validate_action(state, action)
    if action.kind is ActionKind.CREATE_CHARACTER:
        _apply_create_character(state, action)
        return MechanicalResult(action=action, success=True, tags=["character_creation"])
    if action.kind is ActionKind.START_CONVERSATION:
        result = _apply_intent(state, action, rng)
        update_public_perception(state, action, result)
        return result
    if action.kind is ActionKind.RESPOND_WITH:
        result = apply_follow_up(state, action, rng)
        update_public_perception(state, action, result)
        return result
    if action.kind is ActionKind.END_CONVERSATION:
        return _apply_end_conversation(state, action)
    if action.kind is ActionKind.PROPOSE_RECOUPLE:
        result, _outcome = apply_player_proposal(state, action.target_id or "", rng)
        return result
    if action.kind is ActionKind.NPC_PROPOSAL_RESPONSE:
        result, _outcome = apply_npc_proposal_response(state, action.intent_id or "")
        return result
    if action.kind is ActionKind.CHALLENGE_RESPONSE:
        return _apply_challenge_response(state, action, rng)
    if action.kind is ActionKind.HIDEAWAY:
        return _apply_hideaway(state, action)
    if action.kind is ActionKind.CASA_DECISION:
        return _apply_casa_decision(state, action)
    if action.kind is ActionKind.JOIN_GATHER:
        return MechanicalResult(action=action, success=True, tags=["join_gather"])
    if action.kind is ActionKind.AMBIENT:
        result = _apply_ambient(state, action)
        update_public_perception(state, action, result)
        return result
    if action.kind is ActionKind.INTRODUCE_TO:
        return _apply_intro(state, action)
    if action.kind is ActionKind.MOVE:
        return _apply_move(state, action)
    if action.kind is ActionKind.RECOUPLE:
        return MechanicalResult(action=action, success=True, tags=["recouple"])
    raise ValueError(f"action is not implemented: {action.kind}")


def _apply_create_character(state: GameState, action: PlayerAction) -> None:
    if action.payload is None:
        raise ValueError("CREATE_CHARACTER requires payload")
    archetype_id = action.payload.get("archetype_id")
    gender = action.payload.get("gender")
    stats_payload = action.payload.get("stats")
    rerolled = action.payload.get("rerolled", False)
    if not isinstance(archetype_id, str) or not isinstance(gender, str) or not isinstance(stats_payload, dict):
        raise ValueError("CREATE_CHARACTER payload requires archetype_id, gender, and stats")
    create_character(
        state,
        archetype_id=archetype_id,
        gender=Gender(gender),
        stats=PlayerStats.model_validate(stats_payload),
        rerolled=bool(rerolled),
    )


def _apply_intent(state: GameState, action: PlayerAction, rng: SeededRng) -> MechanicalResult:
    target = find_islander(state, action.target_id)
    if action.intent_id is None:
        raise ValueError("intent_id is required for conversation actions")
    intent = get_intent(action.intent_id)
    if intent not in available_intents_for(state, target.id):
        raise ValueError(f"intent is locked for target: {action.intent_id}")
    breakdown = intent_success_breakdown(state, target, intent)
    roll = rng.randint(1, 100)
    success = roll <= breakdown.final_chance
    delta = (
        intent.relationship_deltas.success.model_copy()
        if success
        else intent.relationship_deltas.miss.model_copy()
    )
    attachment_delta = attachment_delta_modifier(target, intent.id, success)
    delta = _add_delta(delta, attachment_delta)
    breakdown.attachment_delta = attachment_delta
    apply_relationship_delta(target, delta)
    return MechanicalResult(
        action=action,
        success=success,
        roll=roll,
        success_chance=breakdown.final_chance,
        chance_breakdown=breakdown,
        relationship_deltas={target.id: delta},
        tags=intent.tags,
    )


def _apply_end_conversation(state: GameState, action: PlayerAction) -> MechanicalResult:
    delta = RelationshipDelta()
    target_id: str | None = None
    if state.active_conversation is not None:
        target = find_islander(state, state.active_conversation.target_id)
        target_id = target.id
        delta = RelationshipDelta(affection=-1)
        apply_relationship_delta(target, delta)
    return MechanicalResult(
        action=action,
        success=True,
        relationship_deltas={} if target_id is None else {target_id: delta},
        tags=["walked_away"],
    )


def _apply_move(state: GameState, action: PlayerAction) -> MechanicalResult:
    if action.target_id is None:
        raise ValueError("target_id is required for MOVE")
    state.location_id = Location(action.target_id)
    state.active_ambient_id = None
    state.consecutive_ambient_turns = 0
    return MechanicalResult(action=action, success=True, tags=["move"])


def _apply_ambient(state: GameState, action: PlayerAction) -> MechanicalResult:
    if action.target_id is None:
        raise ValueError("AMBIENT requires target_id")
    option = get_ambient_option(action.target_id)
    same_context = state.active_ambient_id == option.id
    state.active_ambient_id = option.id
    state.consecutive_ambient_turns = state.consecutive_ambient_turns + 1 if same_context else 1
    for stat_name, amount in option.stat_trickle.items():
        current = getattr(state.player.stats, stat_name)
        setattr(state.player.stats, stat_name, min(9, current + amount))
    tags = ["ambient", option.category, option.mood_effect]
    if state.consecutive_ambient_turns >= 3:
        tags.append("ambient_repeat")
    return MechanicalResult(action=action, success=True, tags=tags)


def _apply_intro(state: GameState, action: PlayerAction) -> MechanicalResult:
    if action.target_id is None or action.intent_id is None:
        raise ValueError("INTRODUCE_TO requires target_id and intent_id")
    target = find_islander(state, action.target_id)
    style = action.intent_id.removeprefix("intro_")
    delta_by_style = {
        "friendly": RelationshipDelta(affection=2, friendship=3),
        "flirty": RelationshipDelta(affection=2, chemistry=3),
        "deep": RelationshipDelta(affection=1, trust=3),
        "banter": RelationshipDelta(affection=1, friendship=2, chemistry=1),
    }
    delta = delta_by_style.get(style, RelationshipDelta(friendship=2))
    apply_relationship_delta(target, delta)
    apply_familiarity(target, 25)
    if target.id not in state.intro_completed_ids:
        state.intro_completed_ids.append(target.id)
    state.active_ambient_id = None
    state.consecutive_ambient_turns = 0
    return MechanicalResult(
        action=action,
        success=True,
        relationship_deltas={target.id: delta},
        tags=["intro", style],
    )


def _apply_challenge_response(state: GameState, action: PlayerAction, rng: SeededRng) -> MechanicalResult:
    if state.pending_challenge is None:
        raise ValueError("CHALLENGE_RESPONSE requires a pending challenge")
    choice = action.target_id
    resolved = resolve_challenge(state, state.pending_challenge, rng, choice=choice)
    state.pending_challenge = resolved
    return MechanicalResult(
        action=action,
        success=resolved.result == "success",
        relationship_deltas=resolved.deltas,
        tags=["challenge", resolved.kind],
    )


def _apply_hideaway(state: GameState, action: PlayerAction) -> MechanicalResult:
    partner_id = state.hideaway.partner_id
    delta = apply_hideaway(state)
    partner_id = state.hideaway.partner_id or partner_id
    return MechanicalResult(
        action=action,
        success=True,
        relationship_deltas={} if partner_id is None else {partner_id: delta},
        tags=HIDEAWAY_TAGS,
    )


def _apply_casa_decision(state: GameState, action: PlayerAction) -> MechanicalResult:
    if action.intent_id is None:
        raise ValueError("CASA_DECISION requires intent_id")
    decision = CasaDecision(action.intent_id)
    apply_casa_decision(state, decision, action.target_id)
    return MechanicalResult(
        action=action,
        success=True,
        tags=["casa_amor", decision.value],
    )


def _add_delta(first: RelationshipDelta, second: RelationshipDelta) -> RelationshipDelta:
    return RelationshipDelta(
        affection=first.affection + second.affection,
        chemistry=first.chemistry + second.chemistry,
        trust=first.trust + second.trust,
        friendship=first.friendship + second.friendship,
    )


__all__ = [
    "ChanceBreakdown",
    "EXIT_INTENT_KINDS",
    "FOLLOW_UP_DELTA_TABLE",
    "INTERRUPTION_INTENT_KINDS",
    "MechanicalResult",
    "apply_action",
    "apply_follow_up",
    "apply_interruption_response",
    "defer_chance",
    "defer_chance_breakdown",
    "follow_up_delta",
    "follow_up_success_breakdown",
    "follow_up_success_chance",
    "intent_success_breakdown",
    "intent_success_chance",
    "update_public_perception",
]
