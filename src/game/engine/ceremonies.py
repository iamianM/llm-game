"""Deterministic pairing, Heart Throb, and elimination ceremonies.

Design sources:
- docs/design/10-Elimination-System.md: pairings, Heart Throbs, Heart Out beats
- docs/design/12-Challenges-And-Events.md: dramatic event timing
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.game.content.loader import load_backstories
from src.game.content.trait_library import heart_throb_trait_cards
from src.game.engine.couples import StealAttempt, resolve_steal_attempt
from src.game.engine.final_vote import final_vote, final_vote_message
from src.game.engine.heart_throb_brief import pick_heart_throb_brief
from src.game.engine.knowledge import reveal_partner_surface_facts
from src.game.state.models import (
    AttachmentStyle,
    Big5,
    Couple,
    GameState,
    Gender,
    HeartbreakerState,
    IdealMatch,
    Location,
    RelationshipState,
)
from src.game.state.rng import SeededRng
from src.game.state.traits import TraitCard


class PairingResult(BaseModel):
    """Resolved ceremony output."""

    model_config = ConfigDict(extra="forbid")

    couples: list[Couple]
    eliminated_id: str | None = None
    steal_attempts: list[StealAttempt] = Field(default_factory=list)


class CeremonyEvent(BaseModel):
    """A visible resort event surfaced to traces and reports."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    message: str
    heartbreaker_id: str | None = None
    sub_kind: str | None = None


def initial_coupling(state: GameState, player_choice_id: str) -> PairingResult:
    """Form the day-one starting couples without heart_out the leftover single."""
    choice = _find_active_heartbreaker(state, player_choice_id)
    if choice.gender == state.player.gender:
        raise ValueError("initial coupling target must be opposite sex")
    available = [
        heartbreaker
        for heartbreaker in state.heartbreakers
        if not heartbreaker.eliminated and heartbreaker.id != choice.id
    ]
    opposite = [heartbreaker for heartbreaker in available if heartbreaker.gender != state.player.gender]
    same = [heartbreaker for heartbreaker in available if heartbreaker.gender == state.player.gender]
    opposite.sort(key=lambda heartbreaker: _partner_score(heartbreaker), reverse=True)
    same.sort(key=lambda heartbreaker: _partner_score(heartbreaker), reverse=True)
    couples = [
        Couple(
            partner_a_id=state.player.id,
            partner_b_id=choice.id,
            formed_on_day=state.day,
            formed_via="opening",
        )
    ]
    choice.familiarity_with_player = max(choice.familiarity_with_player, 25)
    reveal_partner_surface_facts(state, choice.id)
    while opposite and same:
        couples.append(
            Couple(
                partner_a_id=opposite.pop(0).id,
                partner_b_id=same.pop(0).id,
                formed_on_day=state.day,
                formed_via="opening",
            )
        )
    state.couples = couples
    return PairingResult(couples=couples)


def pairing(state: GameState, player_choice_id: str | None = None) -> PairingResult:
    """Pair active players and eliminate one leftover contestant if needed."""
    active = [heartbreaker for heartbreaker in state.heartbreakers if not heartbreaker.eliminated]
    active.sort(key=lambda heartbreaker: _partner_score(heartbreaker), reverse=True)

    couples: list[Couple] = []
    if not state.player.eliminated and active:
        partner_index = _player_partner_index(active, state, player_choice_id)
        if partner_index is not None:
            partner = active.pop(partner_index)
            couples.append(
                Couple(partner_a_id=state.player.id, partner_b_id=partner.id, formed_on_day=state.day)
            )

    npc_couples, leftovers = _npc_opposite_gender_couples(active, state.day)
    couples.extend(npc_couples)

    eliminated_id: str | None = None
    if leftovers:
        leftovers.sort(key=_partner_score)
        eliminated = leftovers[0]
        eliminated.eliminated = True
        eliminated_id = eliminated.id

    if not state.player.eliminated and not any(
        state.player.id in {couple.partner_a_id, couple.partner_b_id} for couple in couples
    ):
        state.player.eliminated = True
        eliminated_id = state.player.id

    state.couples = couples
    steal_attempts = _resolve_heart_throb_steals(state)
    if not state.couples and not state.player.eliminated:
        state.player.eliminated = True
        eliminated_id = state.player.id
    return PairingResult(couples=state.couples, eliminated_id=eliminated_id, steal_attempts=steal_attempts)


def _npc_opposite_gender_couples(active: list[HeartbreakerState], formed_on_day: int) -> tuple[list[Couple], list[HeartbreakerState]]:
    men = [heartbreaker for heartbreaker in active if heartbreaker.gender == Gender.MAN]
    women = [heartbreaker for heartbreaker in active if heartbreaker.gender == Gender.WOMAN]
    men.sort(key=_partner_score, reverse=True)
    women.sort(key=_partner_score, reverse=True)
    couples: list[Couple] = []
    while men and women:
        first = men.pop(0)
        second = women.pop(0)
        couples.append(
            Couple(
                partner_a_id=first.id,
                partner_b_id=second.id,
                formed_via="ceremony",
                formed_on_day=formed_on_day,
            )
        )
    return couples, [*men, *women]


def arrive_heart_throb(state: GameState, location: Location = Location.TERRACE) -> HeartbreakerState:
    """Add the deterministic Phase C Heart Throb once."""
    existing = {heartbreaker.id for heartbreaker in state.heartbreakers}
    if "aisha" in existing:
        for heartbreaker in state.heartbreakers:
            if heartbreaker.id == "aisha":
                return heartbreaker
    brief = pick_heart_throb_brief(state)
    state.heart_throb_briefs.append(brief.model_dump(mode="json"))
    trait_card = _heart_throb_card_for(brief.threat_mode.value)
    heart_throb = HeartbreakerState(
        id="aisha",
        name="Aisha",
        gender=Gender.WOMAN,
        archetype="joker",
        backstory=load_backstories()["aisha"],
        location_id=location,
        relationship=RelationshipState(affection=8, chemistry=12),
        public_perception=55,
        big5=Big5(openness=8, conscientiousness=7, extraversion=9, agreeableness=5, neuroticism=6),
        attachment=AttachmentStyle.AVOIDANT,
        ideal_match=IdealMatch(
            physical_type="bold style and sharp confidence",
            personality_type=["ambitious", "edgy"],
            values=["ambition", "edge"],
            dealbreakers=["neediness"],
        ),
        trait_card=trait_card,
    )
    state.heartbreakers.append(heart_throb)
    return heart_throb


def _heart_throb_card_for(threat_mode: str) -> TraitCard:
    cards = heart_throb_trait_cards()
    for card_id, card in cards.items():
        if threat_mode in _eligible_modes(card_id):
            return card
    return next(iter(cards.values()))


def _eligible_modes(card_id: str) -> set[str]:
    mapping = {
        "sam_ht": {"steal_partner", "tempt_player"},
        "riley_ht": {"inject_chaos", "break_rival"},
        "ellis_ht": {"break_rival", "shake_alliance"},
        "talia_ht": {"tempt_player", "expose_history"},
    }
    return mapping.get(card_id, set())


def final_vote_ceremony(state: GameState) -> CeremonyEvent:
    """Resolve the final vote and return a visible event."""
    result = final_vote(state)
    return CeremonyEvent(kind="final_vote", message=final_vote_message(result, state))


def _partner_score(heartbreaker: HeartbreakerState) -> int:
    rel = heartbreaker.relationship
    return rel.affection + (rel.chemistry // 2) + rel.trust


def _player_partner_index(
    active: list[HeartbreakerState],
    state: GameState,
    player_choice_id: str | None,
) -> int | None:
    if player_choice_id is None:
        for index, heartbreaker in enumerate(active):
            if heartbreaker.gender != state.player.gender:
                return index
        return None
    for index, heartbreaker in enumerate(active):
        if heartbreaker.id == player_choice_id:
            if heartbreaker.gender == state.player.gender:
                raise ValueError("pairing target must be opposite sex")
            return index
    raise ValueError(f"pairing target is not available: {player_choice_id}")


def _find_active_heartbreaker(state: GameState, heartbreaker_id: str) -> HeartbreakerState:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == heartbreaker_id and not heartbreaker.eliminated:
            return heartbreaker
    raise ValueError(f"initial coupling target is not available: {heartbreaker_id}")


def _resolve_heart_throb_steals(state: GameState) -> list[StealAttempt]:
    attempts: list[StealAttempt] = []
    for heart_throb in state.heartbreakers:
        if heart_throb.eliminated or heart_throb.id != "aisha":
            continue
        current = next(
            (couple for couple in state.couples if heart_throb.id in {couple.partner_a_id, couple.partner_b_id}),
            None,
        )
        candidates = [
            couple for couple in state.couples
            if heart_throb.id not in {couple.partner_a_id, couple.partner_b_id}
        ]
        if current is None and candidates:
            target = candidates[0]
        elif current is not None and candidates and heart_throb.relationship.chemistry >= 25:
            target = candidates[0]
        else:
            continue
        attempt = resolve_steal_attempt(state, heart_throb.id, target, _steal_rng(state, heart_throb.id))
        attempts.append(attempt)
    return attempts


def _steal_rng(state: GameState, heart_throb_id: str) -> SeededRng:
    return SeededRng(f"{state.seed}:steal:{state.day}:{heart_throb_id}")
