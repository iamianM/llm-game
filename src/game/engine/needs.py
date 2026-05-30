"""Needs-driven NPC movement — Sims-style location advertisement.

Deterministic engine rules (not an LLM agent; ADR-0003/0007 forbid a Director
agent). Each villa location *advertises* need-satisfaction that shifts with the
phase / time of day. Free NPCs score the reachable locations and drift toward
the strongest pull, with inertia so they don't stampede every turn.

Post-event dispersal is emergent rather than special-cased: the firepit only
advertises strongly in the evening, so when a gather or ceremony ends (the whole
cast clustered at the firepit) everyone re-scores and scatters to wherever
they're motivated to be — bedroom / kitchen in the morning, pool in the
afternoon, terrace / firepit at night.

Design sources:
- docs/engine-issues-from-h11-review.md §9b (ambient loop + npc_encounter)
- GDC "Those Darned Sims: What Makes Them Tick?" (utility/advertisement model)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.game.engine.casa_amor import location_villa, locations_for_villa
from src.game.engine.couples import partner_for
from src.game.state.models import GameState, IslanderState, Location, Phase
from src.game.state.personality import Big5
from src.game.state.rng import SeededRng

LocationRole = Literal["pool", "kitchen", "terrace", "bedroom", "firepit"]

# Each concrete location (main villa + Casa Amor) maps to a role so the
# advertisement table works in either villa. The Hideaway is intentionally
# absent — it is a special couple location, never a needs destination.
ROLE_OF: dict[Location, LocationRole] = {
    Location.POOL: "pool",
    Location.CASA_POOL: "pool",
    Location.KITCHEN: "kitchen",
    Location.CASA_KITCHEN: "kitchen",
    Location.TERRACE: "terrace",
    Location.CASA_TERRACE: "terrace",
    Location.BEDROOM: "bedroom",
    Location.FIREPIT: "firepit",
}

# How strongly each location role pulls NPCs during the free-roam phases.
# CHALLENGE / INTROS are scripted (no needs movement) and COMPLETE is terminal,
# so they are intentionally absent — callers must treat "phase not in table" as
# "no needs movement this turn".
PHASE_ADVERTISEMENT: dict[Phase, dict[LocationRole, int]] = {
    Phase.MORNING: {"bedroom": 30, "kitchen": 28, "pool": 12, "terrace": 12, "firepit": 5},
    Phase.AFTERNOON: {"pool": 32, "kitchen": 16, "terrace": 16, "bedroom": 6, "firepit": 6},
    Phase.TEXT: {"kitchen": 22, "terrace": 22, "pool": 14, "bedroom": 10, "firepit": 10},
    Phase.EVENING: {"terrace": 30, "firepit": 26, "kitchen": 16, "pool": 8, "bedroom": 6},
}

# Hysteresis: an NPC only relocates when the best destination beats their current
# spot by this margin. Keeps the villa from reshuffling wholesale every turn.
MOVE_THRESHOLD = 7
# Inertia bonus added to the NPC's current-location score.
STAY_BONUS = 8
# Per-person social weight, capped, so locations with people present pull
# extraverts and repel introverts without runaway clumping.
SOCIAL_CAP = 10
# A present couple partner is a strong romantic pull.
PARTNER_PULL = 18


class NeedsMovement(BaseModel):
    """One intended needs-driven relocation for an NPC this turn."""

    model_config = ConfigDict(extra="forbid")

    npc_id: str
    from_location: Location
    to_location: Location
    role: LocationRole
    score: int
    reason: str


def reachable_locations(state: GameState) -> list[Location]:
    """Return the needs-eligible locations for the active villa, sorted."""
    return sorted(
        (loc for loc in locations_for_villa(state.villa) if loc in ROLE_OF),
        key=lambda loc: loc.value,
    )


def free_npcs(state: GameState) -> list[IslanderState]:
    """Return NPCs that may be moved this turn.

    Excludes eliminated islanders, anyone locked in an active NPC-NPC
    conversation, and the partner the player is actively talking to. During
    Casa Amor only NPCs already in the *active* villa are eligible: the needs
    layer advertises just this villa's locations, so an islander stranded in
    the other villa would always score ``-999`` for "stay put" and get yanked
    across the divide. Gating here keeps the two villas physically separate.
    """
    locked: set[str] = set()
    for conversation in state.npc_conversations:
        if conversation.status == "active":
            locked.update(conversation.participants)
    active_target = (
        state.active_conversation.target_id if state.active_conversation is not None else None
    )
    return [
        islander
        for islander in state.islanders
        if not islander.eliminated
        and islander.id not in locked
        and islander.id != active_target
        and location_villa(islander.location_id) is state.villa
    ]


def _personality_affinity(role: LocationRole, big5: Big5) -> int:
    """Small secondary pull from personality. Big5 traits are 1-10 (5 = neutral)."""
    if role in ("pool", "firepit"):
        return (big5.extraversion - 5) * 2
    if role == "kitchen":
        return (big5.agreeableness - 5) + (big5.conscientiousness - 5)
    if role == "terrace":
        return (5 - big5.extraversion) + (big5.openness - 5)
    if role == "bedroom":
        return (big5.neuroticism - 5) + (5 - big5.extraversion)
    return 0


def _headcount(state: GameState, location: Location, exclude_id: str) -> int:
    return sum(
        1
        for islander in state.islanders
        if not islander.eliminated
        and islander.id != exclude_id
        and islander.location_id == location
    )


def _social_pull(state: GameState, npc: IslanderState, location: Location) -> int:
    heads = _headcount(state, location, npc.id)
    if heads == 0:
        return 0
    if npc.big5.extraversion > 5:
        per = 2
    elif npc.big5.extraversion < 5:
        per = -2
    else:
        return 0
    return max(-SOCIAL_CAP, min(SOCIAL_CAP, heads * per))


def _romance_pull(state: GameState, npc: IslanderState, location: Location) -> int:
    for couple in state.couples:
        if npc.id not in {couple.partner_a_id, couple.partner_b_id}:
            continue
        partner_id = partner_for(couple, npc.id)
        if partner_id == state.player.id:
            return 0  # the player isn't an NPC we can locate here
        partner = _islander_or_none(state, partner_id)
        if partner is not None and partner.location_id == location:
            return PARTNER_PULL
    return 0


def destination_score(
    state: GameState,
    npc: IslanderState,
    location: Location,
    rng: SeededRng,
) -> int:
    """Total advertised utility of ``location`` for ``npc`` this turn."""
    role = ROLE_OF[location]
    advertisement = PHASE_ADVERTISEMENT.get(state.phase, {})
    score = advertisement.get(role, 0)
    score += _social_pull(state, npc, location)
    score += _romance_pull(state, npc, location)
    score += _personality_affinity(role, npc.big5)
    if location == npc.location_id:
        score += STAY_BONUS
    jitter = rng.fork(
        f"needs:{state.day}:{state.turn_index}:{npc.id}:{location.value}"
    ).randint(0, 6)
    return score + jitter


def plan_needs_movements(state: GameState, rng: SeededRng) -> list[NeedsMovement]:
    """Plan needs-driven relocations for every free NPC this turn.

    Returns the intended moves without mutating state. Deterministic given the
    seed: jitter is forked per (day, turn, npc, location).
    """
    if state.phase not in PHASE_ADVERTISEMENT:
        return []
    reachable = reachable_locations(state)
    if not reachable:
        return []
    moves: list[NeedsMovement] = []
    for npc in free_npcs(state):
        scored = sorted(
            ((loc, destination_score(state, npc, loc, rng)) for loc in reachable),
            key=lambda pair: (-pair[1], pair[0].value),
        )
        best_loc, best_score = scored[0]
        if best_loc == npc.location_id:
            continue
        current_score = next(
            (score for loc, score in scored if loc == npc.location_id),
            -999,
        )
        if best_score - current_score < MOVE_THRESHOLD:
            continue
        role = ROLE_OF[best_loc]
        moves.append(
            NeedsMovement(
                npc_id=npc.id,
                from_location=npc.location_id,
                to_location=best_loc,
                role=role,
                score=best_score,
                reason=f"{npc.name} drawn to the {role} ({state.phase.value})",
            )
        )
    return moves


def apply_needs_movements(state: GameState, moves: list[NeedsMovement]) -> None:
    """Apply planned moves to islander locations."""
    by_id = {islander.id: islander for islander in state.islanders}
    for move in moves:
        islander = by_id.get(move.npc_id)
        if islander is not None and not islander.eliminated:
            islander.location_id = move.to_location


def plan_and_apply(state: GameState, rng: SeededRng) -> list[NeedsMovement]:
    """Plan and apply needs movements in one call; returns the applied moves."""
    moves = plan_needs_movements(state, rng)
    apply_needs_movements(state, moves)
    return moves


def _islander_or_none(state: GameState, islander_id: str) -> IslanderState | None:
    for islander in state.islanders:
        if islander.id == islander_id and not islander.eliminated:
            return islander
    return None
