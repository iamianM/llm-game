"""Hideaway eligibility and rewards."""

from __future__ import annotations

from src.game.engine.couples import couple_strength, partner_for, player_couple
from src.game.engine.memory import add_memory, create_memory
from src.game.engine.state_access import apply_relationship_delta, find_islander
from src.game.state.models import GameState, Location, Phase, RelationshipDelta

HIDEAWAY_THRESHOLD = 70
HIDEAWAY_DAILY_DELTAS = RelationshipDelta(affection=10, chemistry=15, trust=10)
HIDEAWAY_TAGS = ["hideaway_night", "intimate", "committed"]


def hideaway_partner_id(state: GameState) -> str | None:
    """Return the player's Hideaway partner if currently eligible."""
    couple = player_couple(state)
    if couple is None:
        return None
    return partner_for(couple, state.player.id)


def hideaway_eligible(state: GameState) -> bool:
    """Whether the Hideaway action should appear now."""
    couple = player_couple(state)
    if couple is None:
        return False
    return (
        state.phase is Phase.EVENING
        and state.day in {4, 5, 6}
        and state.hideaway.used_on_day is None
        and not couple.has_used_hideaway
        and couple_strength(state, couple) >= HIDEAWAY_THRESHOLD
    )


def apply_hideaway(state: GameState) -> RelationshipDelta:
    """Consume the once-per-run Hideaway reward."""
    if not hideaway_eligible(state):
        raise ValueError("Hideaway is not available")
    partner_id = hideaway_partner_id(state)
    if partner_id is None:
        raise ValueError("Hideaway requires a player couple")
    partner = find_islander(state, partner_id)
    apply_relationship_delta(partner, HIDEAWAY_DAILY_DELTAS)
    state.location_id = Location.HIDEAWAY
    partner.location_id = Location.HIDEAWAY
    state.hideaway.used_on_day = state.day
    state.hideaway.partner_id = partner.id
    state.hideaway.deltas_applied = True
    couple = player_couple(state)
    if couple is not None:
        couple.has_used_hideaway = True
    _remember_hideaway(state, partner.id)
    return HIDEAWAY_DAILY_DELTAS


def _remember_hideaway(state: GameState, partner_id: str) -> None:
    partner = find_islander(state, partner_id)
    add_memory(
        state,
        create_memory(
            holder_id=state.player.id,
            subject_id=partner.id,
            source="direct",
            day=state.day,
            turn=state.turn_index,
            weight=9,
            tags=HIDEAWAY_TAGS,
            content=f"The Hideaway with {partner.name} felt private, committed, and hard to fake.",
        ),
    )
    add_memory(
        state,
        create_memory(
            holder_id=partner.id,
            subject_id=state.player.id,
            source="direct",
            day=state.day,
            turn=state.turn_index,
            weight=9,
            tags=HIDEAWAY_TAGS,
            content="The Hideaway made the player's commitment feel much more real.",
        ),
    )
