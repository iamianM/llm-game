"""Casa Amor flow and return ceremony."""

from __future__ import annotations

from src.game.engine.ceremonies import CeremonyEvent
from src.game.engine.couples import partner_for, player_couple
from src.game.engine.memory import add_memory, create_memory, remember_ceremony_events
from src.game.engine.state_access import find_islander
from src.game.state.casa import CasaDecision, VillaName
from src.game.state.models import (
    AttachmentStyle,
    Big5,
    CasaAmorState,
    Couple,
    GameState,
    Gender,
    IslanderState,
    Location,
    RelationshipState,
    TypeOnPaper,
    clamp_relationship,
)
from src.game.state.rng import SeededRng

CASA_LOCATIONS = {Location.CASA_POOL, Location.CASA_KITCHEN, Location.CASA_TERRACE}
MAIN_LOCATIONS = {Location.POOL, Location.KITCHEN, Location.TERRACE, Location.BEDROOM, Location.HIDEAWAY}


def location_villa(location: Location) -> VillaName:
    """Map a location to its villa."""
    return VillaName.CASA_AMOR if location in CASA_LOCATIONS else VillaName.MAIN


def locations_for_villa(villa: VillaName) -> set[Location]:
    """Return legal player/NPC locations for a villa."""
    return CASA_LOCATIONS if villa is VillaName.CASA_AMOR else MAIN_LOCATIONS


def enter_casa_amor(state: GameState) -> CeremonyEvent:
    """Split the villa and add the fixed Casa Amor cast."""
    if state.casa_amor_state is not None:
        return CeremonyEvent(kind="casa_amor_arrival", message="Casa Amor is already underway.")
    partner = player_couple(state)
    original_partner_id = None if partner is None else partner_for(partner, state.player.id)
    casa_cast = _ensure_casa_cast(state)
    for islander in casa_cast:
        islander.location_id = Location.CASA_POOL
    state.villa = VillaName.CASA_AMOR
    state.location_id = Location.CASA_POOL
    state.casa_amor_state = CasaAmorState(
        started_on_day=state.day,
        original_partner_id=original_partner_id,
        casa_islander_ids=[islander.id for islander in casa_cast],
        main_villa_partner_ids=[islander.id for islander in state.islanders if islander.id not in {i.id for i in casa_cast}],
        player_perception_before=state.player.public_perception,
    )
    return CeremonyEvent(kind="casa_amor_arrival", message="Casa Amor begins: the player is sent to the second villa.")


def casa_decision_options(state: GameState) -> list[tuple[CasaDecision, str | None, str]]:
    """Return player-facing Casa Amor decision options."""
    if (
        state.casa_amor_state is None
        or state.casa_amor_state.player_decision is not None
        or state.villa is not VillaName.CASA_AMOR
        or state.day != 5
        or state.phase.value != "evening"
    ):
        return []
    options = [(CasaDecision.RETURN_WITH_ORIGINAL, state.casa_amor_state.original_partner_id, "Return with original partner")]
    for islander_id in state.casa_amor_state.casa_islander_ids[:3]:
        islander = find_islander(state, islander_id)
        options.append((CasaDecision.RETURN_WITH_NEW, islander.id, f"Return with {islander.name}"))
    options.append((CasaDecision.RETURN_SINGLE, None, "Return single"))
    return options


def apply_casa_decision(state: GameState, decision: CasaDecision, partner_id: str | None) -> CeremonyEvent:
    """Record the player's Casa Amor return decision and apply immediate stakes."""
    casa = _active_casa(state)
    casa.player_decision = decision
    casa.chosen_partner_id = partner_id
    if decision is CasaDecision.RETURN_WITH_ORIGINAL:
        _adjust_player_perception(state, 10)
        if casa.original_partner_id is not None:
            find_islander(state, casa.original_partner_id).relationship.trust = clamp_relationship(
                find_islander(state, casa.original_partner_id).relationship.trust + 5
            )
    elif decision is CasaDecision.RETURN_WITH_NEW:
        _adjust_player_perception(state, -12)
        casa.partners_swapped = True
    else:
        _adjust_player_perception(state, 3)
    casa.player_perception_after = state.player.public_perception
    return CeremonyEvent(kind="casa_amor_decision", message=f"Casa Amor decision recorded: {decision.value}.")


def return_ceremony(state: GameState) -> CeremonyEvent | None:
    """Resolve the day-six Casa Amor return reveal."""
    casa = state.casa_amor_state
    if casa is None or casa.returned or casa.player_decision is None:
        return None
    state.villa = VillaName.MAIN
    state.location_id = Location.POOL
    if casa.player_decision is CasaDecision.RETURN_WITH_ORIGINAL and casa.original_partner_id is not None:
        state.couples = [Couple(partner_a_id="player", partner_b_id=casa.original_partner_id, formed_on_day=state.day)]
    elif casa.player_decision is CasaDecision.RETURN_WITH_NEW and casa.chosen_partner_id is not None:
        state.couples = [Couple(partner_a_id="player", partner_b_id=casa.chosen_partner_id, formed_on_day=state.day)]
    else:
        state.couples = [couple for couple in state.couples if "player" not in {couple.partner_a_id, couple.partner_b_id}]
    for islander in state.islanders:
        if not islander.eliminated:
            islander.location_id = Location.POOL
    casa.returned = True
    event = CeremonyEvent(
        kind="casa_amor_return_reveal",
        message=f"Casa Amor return reveal: player chose {casa.player_decision.value}.",
        islander_id=casa.chosen_partner_id or casa.original_partner_id,
    )
    _remember_return(state, event)
    return event


def compute_npc_casa_choices(state: GameState, rng: SeededRng) -> dict[str, str]:
    """Deterministic placeholder choices for NPC Casa Amor outcomes."""
    choices: dict[str, str] = {}
    for islander in state.islanders:
        if islander.eliminated or islander.id == "player":
            continue
        choices[islander.id] = "twist" if rng.randint(1, 100) <= islander.relationship.chemistry else "stick"
    return choices


def _ensure_casa_cast(state: GameState) -> list[IslanderState]:
    existing = {islander.id for islander in state.islanders}
    cast = []
    for islander in _casa_cast():
        if islander.id not in existing:
            state.islanders.append(islander)
            cast.append(islander)
        else:
            cast.append(find_islander(state, islander.id))
    return cast


def _casa_cast() -> list[IslanderState]:
    return [
        _casa("blake", "Blake", Gender.MAN, "smooth", 9, "secure", Location.CASA_POOL),
        _casa("jordan", "Jordan", Gender.MAN, "sweetheart", 7, "anxious", Location.CASA_KITCHEN),
        _casa("marcus", "Marcus", Gender.MAN, "heartthrob", 10, "avoidant", Location.CASA_TERRACE),
        _casa("sophie", "Sophie", Gender.WOMAN, "joker", 8, "secure", Location.CASA_POOL),
        _casa("zara", "Zara", Gender.WOMAN, "bombshell", 12, "avoidant", Location.CASA_KITCHEN),
        _casa("nia", "Nia", Gender.WOMAN, "friend", 6, "anxious", Location.CASA_TERRACE),
    ]


def _casa(
    islander_id: str,
    name: str,
    gender: Gender,
    archetype: str,
    chemistry: int,
    attachment: str,
    location: Location,
) -> IslanderState:
    return IslanderState(
        id=islander_id,
        name=name,
        gender=gender,
        archetype=archetype,
        location_id=location,
        relationship=RelationshipState(affection=12, chemistry=chemistry),
        public_perception=52,
        big5=Big5(openness=7, conscientiousness=6, extraversion=8, agreeableness=6, neuroticism=5),
        attachment=AttachmentStyle(attachment),
        type_on_paper=TypeOnPaper(
            physical_type="fresh Casa Amor confidence",
            personality_type=["curious", "bold"],
            values=["chemistry", "honesty"],
            dealbreakers=["game playing"],
        ),
    )


def _active_casa(state: GameState) -> CasaAmorState:
    if state.casa_amor_state is None:
        raise ValueError("Casa Amor is not active")
    return state.casa_amor_state


def _adjust_player_perception(state: GameState, delta: int) -> None:
    state.player.public_perception = clamp_relationship(state.player.public_perception + delta)


def _remember_return(state: GameState, event: CeremonyEvent) -> None:
    remember_ceremony_events(state, [event])
    for islander in state.islanders:
        if not islander.eliminated:
            add_memory(
                state,
                create_memory(
                    holder_id=islander.id,
                    subject_id="player",
                    source="witnessed",
                    day=state.day,
                    turn=state.turn_index,
                    weight=9,
                    tags=["casa_amor", "return_reveal"],
                    content=event.message,
                ),
            )
