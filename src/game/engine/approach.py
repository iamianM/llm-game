"""Ambient NPC approach mechanics — being "sought after" while idle.

The idle-state sibling of ``engine/interruptions.py``. When the player takes an
AMBIENT turn (no active conversation), co-located NPCs may seek them out: an NPC
walks up to the unoccupied player, and the player chooses how to receive them.

This is what makes idling feel alive instead of dead air — the user's explicit
ask that "when ambient I should be sought after, and ignoring them should affect
the relationship." The four responses mirror docs §9b's approach decline menu:

- Engage              warmly receive them; opens a conversation (turn.py)
- Wave off politely   "not right now" — a small, drama-free cool-off
- Wave off firmly     brush them off hard; they leave and it seeds gossip
- Pretend not to notice  the awkward freeze; they drift away, no public snub

An NPC's *desire* to approach blends relationship warmth, extraversion, recent
gossip pressure about the player, and how socially open the player's current
ambient activity is (the ambient option's ``npc_encounter_boost``).
"""

from __future__ import annotations

from src.game.content.ambient import get_ambient_option
from src.game.engine.actions import PlayerAction
from src.game.engine.casa_amor import locations_for_villa
from src.game.engine.interruptions import remember_interruption_snub
from src.game.engine.results import ForcedMovement, MechanicalResult
from src.game.engine.state_access import apply_relationship_delta, find_islander
from src.game.state.autonomy import ApproachReason, PendingNPCApproach
from src.game.state.models import GameState, IslanderState, Location, RelationshipDelta
from src.game.state.rng import SeededRng

APPROACH_INTENT_KINDS = {
    "engage_approach",
    "wave_off_politely",
    "wave_off_firmly",
    "ignore_approach",
}

# Floor desire so a co-located NPC always has *some* pull while the player idles.
APPROACH_BASE = 6
# Desire is read directly as a percent chance; cap so idling never feels swarmed.
APPROACH_CAP = 80


def approach_candidates(state: GameState) -> list[IslanderState]:
    """Free, co-located NPCs who could seek out the idle player.

    Excludes eliminated islanders and anyone locked in an active NPC-NPC
    conversation — they are busy elsewhere and cannot also approach.
    """
    locked: set[str] = set()
    for conversation in state.npc_conversations:
        if conversation.status == "active":
            locked.update(conversation.participants)
    return [
        islander
        for islander in state.islanders
        if not islander.eliminated
        and islander.id not in locked
        and islander.location_id == state.location_id
    ]


def approach_chance(state: GameState, npc: IslanderState, encounter_boost: int | None = None) -> int:
    """Percent chance that ``npc`` walks up to the idle player this turn."""
    if encounter_boost is None:
        encounter_boost = _ambient_encounter_boost(state)
    rel = npc.relationship
    chance = APPROACH_BASE
    chance += rel.chemistry // 3
    chance += rel.affection // 5
    chance += (npc.big5.extraversion - 5) * 2
    chance += _recent_player_gossip(npc) * 6
    chance += encounter_boost
    chance += _mood_modifier(npc)
    return max(0, min(APPROACH_CAP, chance))


def roll_ambient_approach(state: GameState, rng: SeededRng) -> PendingNPCApproach | None:
    """Roll whether a co-located NPC seeks out the idle player; set it if so.

    At most one approach is pending at a time (like ``pending_interruption``).
    The most-motivated NPC gets first crack, but each roll is independent and
    deterministic via a per-NPC fork.
    """
    if state.pending_npc_approach is not None:
        return state.pending_npc_approach
    boost = _ambient_encounter_boost(state)
    scored = sorted(
        ((npc, approach_chance(state, npc, boost)) for npc in approach_candidates(state)),
        key=lambda pair: (-pair[1], pair[0].id),
    )
    for npc, chance in scored:
        roll = rng.fork(f"approach:{state.day}:{state.turn_index}:{npc.id}").randint(1, 100)
        if roll <= chance:
            approach = PendingNPCApproach(
                npc_id=npc.id,
                location_id=npc.location_id.value,
                reason=_approach_reason(npc),
                warmth="intense" if chance >= 55 else "keen" if chance >= 30 else "casual",
                desire=chance,
            )
            state.pending_npc_approach = approach
            return approach
    return None


def apply_approach_response(
    state: GameState,
    action: PlayerAction,
    rng: SeededRng,
) -> MechanicalResult:
    """Apply one of the code-owned approach response options.

    ``engage_approach`` only books the relationship credit and clears the
    pending approach — turn.py opens the actual conversation (it owns the
    dialogue agents), exactly as ``accept_interruption`` is handled.
    """
    approach = state.pending_npc_approach
    if approach is None:
        raise ValueError("approach response requires a pending approach")
    npc = find_islander(state, approach.npc_id)
    intent_id = action.intent_id
    tags = ["approach", str(intent_id), approach.reason, approach.warmth]
    deltas: dict[str, RelationshipDelta] = {}
    forced_movements: list[ForcedMovement] = []

    if intent_id == "engage_approach":
        delta = RelationshipDelta(affection=2, friendship=1)
        apply_relationship_delta(npc, delta)
        deltas = {npc.id: delta}
        # Engaging consumes the idle context — turn.py opens a conversation.
        state.active_ambient_id = None
        state.consecutive_ambient_turns = 0
    elif intent_id == "wave_off_politely":
        delta = RelationshipDelta(affection=-1)
        apply_relationship_delta(npc, delta)
        deltas = {npc.id: delta}
    elif intent_id == "wave_off_firmly":
        delta = RelationshipDelta(affection=-4)
        apply_relationship_delta(npc, delta)
        deltas = {npc.id: delta}
        remember_interruption_snub(state, npc.id, "brushed_off_in_public", 7)
        target_location = _walkaway_location(state, npc, rng)
        npc.location_id = target_location
        forced_movements.append(
            ForcedMovement(
                actor_id=npc.id,
                kind="walks_away_after_brush_off",
                target_location=target_location,
            )
        )
    elif intent_id == "ignore_approach":
        delta = RelationshipDelta(affection=-2)
        apply_relationship_delta(npc, delta)
        deltas = {npc.id: delta}
        target_location = _walkaway_location(state, npc, rng)
        npc.location_id = target_location
        forced_movements.append(
            ForcedMovement(
                actor_id=npc.id,
                kind="drifts_away_unnoticed",
                target_location=target_location,
            )
        )
    else:
        raise ValueError(f"unknown approach response: {intent_id}")

    state.pending_npc_approach = None
    return MechanicalResult(
        action=action.model_copy(update={"target_id": npc.id}),
        success=True,
        relationship_deltas=deltas,
        tags=tags,
        forced_movements=forced_movements,
    )


def _approach_reason(npc: IslanderState) -> ApproachReason:
    if _recent_player_gossip(npc) > 0:
        return "has_gossip"
    if npc.relationship.chemistry >= 25:
        return "flirty"
    if npc.relationship.affection >= 20 or npc.relationship.friendship >= 20:
        return "wants_to_chat"
    return "curious"


def _ambient_encounter_boost(state: GameState) -> int:
    if state.active_ambient_id is None:
        return 0
    try:
        return get_ambient_option(state.active_ambient_id).npc_encounter_boost
    except ValueError:
        return 0


def _recent_player_gossip(islander: IslanderState) -> int:
    return sum(
        1
        for memory in islander.memories[-5:]
        if memory.subject_id == "player" and memory.emotional_weight >= 5
    )


def _mood_modifier(islander: IslanderState) -> int:
    if islander.mood.value == "flirty":
        return 6
    if islander.mood.value == "happy":
        return 3
    if islander.mood.value in {"upset", "anxious", "angry"}:
        return -4
    return 0


def _walkaway_location(state: GameState, npc: IslanderState, rng: SeededRng) -> Location:
    candidates = [
        location
        for location in sorted(locations_for_villa(state.villa), key=lambda item: item.value)
        if location != npc.location_id and location is not Location.HIDEAWAY
    ]
    if not candidates:
        return npc.location_id
    return rng.choice(candidates)
