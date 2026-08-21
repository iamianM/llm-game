"""Private Suite eligibility and rewards."""

from __future__ import annotations

from src.game.engine.ceremonies import CeremonyEvent
from src.game.engine.couples import couple_strength, partner_for, player_couple
from src.game.engine.memory import add_memory, create_memory
from src.game.engine.state_access import (
    apply_relationship_delta,
    find_heartbreaker,
    player_display_name,
)
from src.game.state.memory import RecapDisposition
from src.game.state.models import GameState, Location, Phase, RelationshipDelta

PRIVATE_SUITE_THRESHOLD = 70
PRIVATE_SUITE_DAILY_DELTAS = RelationshipDelta(affection=10, chemistry=15, trust=10)
PRIVATE_SUITE_TAGS = ["private_suite_night", "intimate", "committed"]


def private_suite_partner_id(state: GameState) -> str | None:
    """Return the player's Private Suite partner if currently eligible."""
    couple = player_couple(state)
    if couple is None:
        return None
    return partner_for(couple, state.player.id)


def private_suite_eligible(state: GameState) -> bool:
    """Whether the Private Suite action should appear now."""
    couple = player_couple(state)
    if couple is None:
        return False
    return (
        state.phase is Phase.EVENING
        and state.day in {4, 5, 6}
        and state.private_suite.used_on_day is None
        and not couple.has_used_private_suite
        and couple_strength(state, couple) >= PRIVATE_SUITE_THRESHOLD
    )


def apply_private_suite(state: GameState) -> RelationshipDelta:
    """Consume the once-per-run Private Suite reward."""
    if not private_suite_eligible(state):
        raise ValueError("Private Suite is not available")
    partner_id = private_suite_partner_id(state)
    if partner_id is None:
        raise ValueError("Private Suite requires a player couple")
    partner = find_heartbreaker(state, partner_id)
    apply_relationship_delta(partner, PRIVATE_SUITE_DAILY_DELTAS)
    state.location_id = Location.PRIVATE_SUITE
    partner.location_id = Location.PRIVATE_SUITE
    state.private_suite.used_on_day = state.day
    state.private_suite.partner_id = partner.id
    state.private_suite.deltas_applied = True
    couple = player_couple(state)
    if couple is not None:
        couple.has_used_private_suite = True
    _remember_private_suite(state, partner.id)
    return PRIVATE_SUITE_DAILY_DELTAS


def private_suite_event(state: GameState) -> CeremonyEvent:
    """Return the visible event created by the consumed Private Suite reward."""
    partner_id = state.private_suite.partner_id
    if partner_id is None:
        raise ValueError("Private Suite event requires a consumed Private Suite partner")
    partner = find_heartbreaker(state, partner_id)
    return CeremonyEvent(
        kind="private_suite",
        message=f"{player_display_name(state)} and {partner.name} leave for a private Paradise Suite night.",
        heartbreaker_id=partner.id,
        participant_ids=[state.player.id, partner.id],
    )


def _remember_private_suite(state: GameState, partner_id: str) -> None:
    partner = find_heartbreaker(state, partner_id)
    add_memory(
        state,
        create_memory(
            holder_id=state.player.id,
            subject_id=partner.id,
            source="direct",
            day=state.day,
            turn=state.turn_index,
            weight=9,
            tags=PRIVATE_SUITE_TAGS,
            content=f"The Private Suite with {partner.name} felt private, committed, and hard to fake.",
            recap_disposition=RecapDisposition.YOUR_DAY,
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
            tags=PRIVATE_SUITE_TAGS,
            content="The Private Suite made the player's commitment feel much more real.",
            recap_disposition=RecapDisposition.YOUR_DAY,
        ),
    )
