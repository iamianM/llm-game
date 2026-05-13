"""Deterministic recoupling, bombshell, and elimination ceremonies.

Design sources:
- 10-Elimination-System.md: recouplings, bombshells, dumping
- 12-Challenges-And-Events.md: dramatic event timing
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.game.engine.couples import StealAttempt, resolve_steal_attempt
from src.game.engine.final_vote import final_vote, final_vote_message
from src.game.state.models import (
    AttachmentStyle,
    Big5,
    Couple,
    GameState,
    Gender,
    IslanderState,
    Location,
    RelationshipState,
    TypeOnPaper,
)
from src.game.state.rng import SeededRng


class RecouplingResult(BaseModel):
    """Resolved ceremony output."""

    model_config = ConfigDict(extra="forbid")

    couples: list[Couple]
    eliminated_id: str | None = None
    steal_attempts: list[StealAttempt] = Field(default_factory=list)


class CeremonyEvent(BaseModel):
    """A visible villa event surfaced to traces and reports."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    message: str
    islander_id: str | None = None


def initial_coupling(state: GameState, player_choice_id: str) -> RecouplingResult:
    """Form the day-one starting couples without dumping the leftover single."""
    choice = _find_active_islander(state, player_choice_id)
    if choice.gender == state.player.gender:
        raise ValueError("initial coupling target must be opposite sex")
    available = [
        islander
        for islander in state.islanders
        if not islander.eliminated and islander.id != choice.id
    ]
    opposite = [islander for islander in available if islander.gender != state.player.gender]
    same = [islander for islander in available if islander.gender == state.player.gender]
    opposite.sort(key=lambda islander: _partner_score(islander), reverse=True)
    same.sort(key=lambda islander: _partner_score(islander), reverse=True)
    couples = [Couple(partner_a_id=state.player.id, partner_b_id=choice.id, formed_on_day=state.day)]
    while opposite and same:
        couples.append(
            Couple(
                partner_a_id=opposite.pop(0).id,
                partner_b_id=same.pop(0).id,
                formed_on_day=state.day,
            )
        )
    state.couples = couples
    return RecouplingResult(couples=couples)


def recoupling(state: GameState, player_choice_id: str | None = None) -> RecouplingResult:
    """Pair active players and eliminate one leftover contestant if needed."""
    active = [islander for islander in state.islanders if not islander.eliminated]
    active.sort(key=lambda islander: _partner_score(islander), reverse=True)

    couples: list[Couple] = []
    if not state.player.eliminated and active:
        partner_index = _partner_index(active, player_choice_id)
        partner = active.pop(partner_index)
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
    steal_attempts = _resolve_bombshell_steals(state)
    if not state.couples and not state.player.eliminated:
        state.player.eliminated = True
        eliminated_id = state.player.id
    return RecouplingResult(couples=state.couples, eliminated_id=eliminated_id, steal_attempts=steal_attempts)


def arrive_bombshell(state: GameState, location: Location = Location.TERRACE) -> IslanderState:
    """Add the deterministic Phase C bombshell once."""
    existing = {islander.id for islander in state.islanders}
    if "aisha" in existing:
        for islander in state.islanders:
            if islander.id == "aisha":
                return islander
    bombshell = IslanderState(
        id="aisha",
        name="Aisha",
        gender=Gender.WOMAN,
        archetype="joker",
        location_id=location,
        relationship=RelationshipState(affection=8, chemistry=12),
        public_perception=55,
        big5=Big5(openness=8, conscientiousness=7, extraversion=9, agreeableness=5, neuroticism=6),
        attachment=AttachmentStyle.AVOIDANT,
        type_on_paper=TypeOnPaper(
            physical_type="bold style and sharp confidence",
            personality_type=["ambitious", "edgy"],
            values=["ambition", "edge"],
            dealbreakers=["neediness"],
        ),
    )
    state.islanders.append(bombshell)
    return bombshell


def final_vote_ceremony(state: GameState) -> CeremonyEvent:
    """Resolve the final vote and return a visible event."""
    result = final_vote(state)
    return CeremonyEvent(kind="final_vote", message=final_vote_message(result))


def _partner_score(islander: IslanderState) -> int:
    rel = islander.relationship
    return rel.affection + (rel.chemistry // 2) + rel.trust


def _partner_index(active: list[IslanderState], player_choice_id: str | None) -> int:
    if player_choice_id is None:
        return 0
    for index, islander in enumerate(active):
        if islander.id == player_choice_id:
            return index
    raise ValueError(f"recoupling target is not available: {player_choice_id}")


def _find_active_islander(state: GameState, islander_id: str) -> IslanderState:
    for islander in state.islanders:
        if islander.id == islander_id and not islander.eliminated:
            return islander
    raise ValueError(f"initial coupling target is not available: {islander_id}")


def _resolve_bombshell_steals(state: GameState) -> list[StealAttempt]:
    attempts: list[StealAttempt] = []
    for bombshell in state.islanders:
        if bombshell.eliminated or bombshell.id != "aisha":
            continue
        current = next(
            (couple for couple in state.couples if bombshell.id in {couple.partner_a_id, couple.partner_b_id}),
            None,
        )
        candidates = [
            couple for couple in state.couples
            if bombshell.id not in {couple.partner_a_id, couple.partner_b_id}
        ]
        if current is None and candidates:
            target = candidates[0]
        elif current is not None and candidates and bombshell.relationship.chemistry >= 25:
            target = candidates[0]
        else:
            continue
        attempt = resolve_steal_attempt(state, bombshell.id, target, _steal_rng(state, bombshell.id))
        attempts.append(attempt)
    return attempts


def _steal_rng(state: GameState, bombshell_id: str) -> SeededRng:
    return SeededRng(f"{state.seed}:steal:{state.day}:{bombshell_id}")
