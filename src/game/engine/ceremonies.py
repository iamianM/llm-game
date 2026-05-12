"""Deterministic recoupling, bombshell, and elimination ceremonies.

Design sources:
- 10-Elimination-System.md: recouplings, bombshells, dumping
- 12-Challenges-And-Events.md: dramatic event timing
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.game.state.models import Couple, GameState, IslanderState, Location, RelationshipState
from src.game.state.rng import SeededRng


class RecouplingResult(BaseModel):
    """Resolved ceremony output."""

    model_config = ConfigDict(extra="forbid")

    couples: list[Couple]
    eliminated_id: str | None = None


def recoupling(state: GameState, rng: SeededRng) -> RecouplingResult:
    """Pair active players and eliminate one leftover contestant if needed."""
    active = [islander for islander in state.islanders if not islander.eliminated]
    active.sort(key=lambda islander: _partner_score(islander), reverse=True)

    couples: list[Couple] = []
    if not state.player.eliminated and active:
        partner = active.pop(0)
        couples.append(
            Couple(partner_a_id=state.player.id, partner_b_id=partner.id, formed_on_day=state.day)
        )

    while len(active) >= 2:
        first = active.pop(0)
        second = active.pop(0)
        couples.append(Couple(partner_a_id=first.id, partner_b_id=second.id, formed_on_day=state.day))

    eliminated_id: str | None = None
    if active:
        eliminated = active.pop(0)
        eliminated.eliminated = True
        eliminated_id = eliminated.id

    state.couples = couples
    if not state.couples and not state.player.eliminated:
        state.player.eliminated = True
        eliminated_id = state.player.id
    return RecouplingResult(couples=couples, eliminated_id=eliminated_id)


def arrive_bombshell(state: GameState, rng: SeededRng) -> IslanderState:
    """Add the deterministic Phase C bombshell once."""
    existing = {islander.id for islander in state.islanders}
    if "aisha" in existing:
        for islander in state.islanders:
            if islander.id == "aisha":
                return islander
    bombshell = IslanderState(
        id="aisha",
        name="Aisha",
        archetype="joker",
        location_id=rng.choice(list(Location)),
        relationship=RelationshipState(affection=8, chemistry=12),
        public_perception=55,
    )
    state.islanders.append(bombshell)
    return bombshell


def _partner_score(islander: IslanderState) -> int:
    rel = islander.relationship
    return rel.affection + (rel.chemistry // 2) + rel.trust
