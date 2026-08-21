"""Flush of Hearts flow and return ceremony."""

from __future__ import annotations

from src.game.content.loader import load_content
from src.game.content.models import FlushOfHeartsCastContent
from src.game.content.trait_library import heart_throb_trait_cards
from src.game.engine.ceremonies import CeremonyEvent
from src.game.engine.couples import partner_for, player_couple
from src.game.engine.heart_throb_brief import pick_heart_throb_brief
from src.game.engine.memory import add_memory, create_memory, remember_ceremony_events
from src.game.engine.state_access import display_name, find_heartbreaker
from src.game.state.flush import FlushDecision, ResortName
from src.game.state.memory import RecapDisposition
from src.game.state.models import (
    AttachmentStyle,
    Big5,
    Couple,
    FlushOfHeartsState,
    GameState,
    Gender,
    HeartbreakerState,
    IdealMatch,
    Location,
    RelationshipState,
    clamp_relationship,
)
from src.game.state.rng import SeededRng
from src.game.state.traits import TraitCard

FLUSH_LOCATIONS = {Location.FLUSH_POOL, Location.FLUSH_KITCHEN, Location.FLUSH_TERRACE}
MAIN_LOCATIONS = {
    Location.POOL,
    Location.KITCHEN,
    Location.TERRACE,
    Location.BEDROOM,
    Location.FLAME_DECK,
    Location.PRIVATE_SUITE,
}


def location_resort(location: Location) -> ResortName:
    """Map a location to its resort."""
    return ResortName.FLUSH_OF_HEARTS if location in FLUSH_LOCATIONS else ResortName.MAIN


def locations_for_resort(resort: ResortName) -> set[Location]:
    """Return legal player/NPC locations for a resort."""
    return FLUSH_LOCATIONS if resort is ResortName.FLUSH_OF_HEARTS else MAIN_LOCATIONS


def enter_flush_of_hearts(state: GameState) -> CeremonyEvent:
    """Split the resort and add the fixed Flush of Hearts cast."""
    if state.flush_of_hearts_state is not None:
        return CeremonyEvent(kind="flush_of_hearts_arrival", message="Flush of Hearts is already underway.")
    partner = player_couple(state)
    original_partner_id = None if partner is None else partner_for(partner, state.player.id)
    flush_cast = _ensure_flush_cast(state)
    brief = pick_heart_throb_brief(state)
    state.heart_throb_briefs.append(brief.model_dump(mode="json"))
    for heartbreaker in flush_cast:
        heartbreaker.location_id = Location.FLUSH_POOL
    state.resort = ResortName.FLUSH_OF_HEARTS
    state.location_id = Location.FLUSH_POOL
    state.flush_of_hearts_state = FlushOfHeartsState(
        started_on_day=state.day,
        original_partner_id=original_partner_id,
        flush_heartbreaker_ids=[heartbreaker.id for heartbreaker in flush_cast],
        sunset_bay_partner_ids=[heartbreaker.id for heartbreaker in state.heartbreakers if heartbreaker.id not in {i.id for i in flush_cast}],
        player_perception_before=state.player.public_perception,
    )
    participant_ids = ["player"]
    if original_partner_id is None:
        message = (
            "Flush of Hearts begins: "
            f"{display_name(state, 'player')} is sent to the Flush resort."
        )
    else:
        participant_ids.append(original_partner_id)
        original_partner = display_name(state, original_partner_id)
        message = (
            "Flush of Hearts begins: "
            f"{display_name(state, 'player')} is sent to the Flush resort while "
            f"{original_partner} remains at Sunset Bay; their connection is now "
            "tested at a distance."
        )
    return CeremonyEvent(
        kind="flush_of_hearts_arrival",
        message=message,
        participant_ids=participant_ids,
    )


def flush_decision_options(state: GameState) -> list[tuple[FlushDecision, str | None, str]]:
    """Return player-facing Flush of Hearts decision options."""
    if (
        state.flush_of_hearts_state is None
        or state.flush_of_hearts_state.player_decision is not None
        or state.resort is not ResortName.FLUSH_OF_HEARTS
        or state.day != 5
        or state.phase.value != "evening"
    ):
        return []
    options = [(FlushDecision.RETURN_WITH_ORIGINAL, state.flush_of_hearts_state.original_partner_id, "Return with original partner")]
    for heartbreaker_id in state.flush_of_hearts_state.flush_heartbreaker_ids[:3]:
        heartbreaker = find_heartbreaker(state, heartbreaker_id)
        options.append((FlushDecision.RETURN_WITH_NEW, heartbreaker.id, f"Return with {heartbreaker.name}"))
    options.append((FlushDecision.RETURN_SINGLE, None, "Return single"))
    return options


def apply_flush_decision(state: GameState, decision: FlushDecision, partner_id: str | None) -> CeremonyEvent:
    """Record the player's Flush return decision and apply immediate stakes."""
    flush = _active_flush(state)
    flush.player_decision = decision
    flush.chosen_partner_id = partner_id
    if decision is FlushDecision.RETURN_WITH_ORIGINAL:
        _adjust_player_perception(state, 10)
        if flush.original_partner_id is not None:
            find_heartbreaker(state, flush.original_partner_id).relationship.trust = clamp_relationship(
                find_heartbreaker(state, flush.original_partner_id).relationship.trust + 5
            )
    elif decision is FlushDecision.RETURN_WITH_NEW:
        _adjust_player_perception(state, -12)
        flush.partners_swapped = True
    else:
        _adjust_player_perception(state, 3)
    flush.player_perception_after = state.player.public_perception
    return CeremonyEvent(
        kind="flush_of_hearts_decision",
        message=flush_decision_message(state, decision, partner_id),
        heartbreaker_id=partner_id,
    )


def return_ceremony(state: GameState) -> CeremonyEvent | None:
    """Resolve the day-six Flush return reveal."""
    flush = state.flush_of_hearts_state
    if flush is None or flush.returned or flush.player_decision is None:
        return None
    state.resort = ResortName.MAIN
    state.location_id = Location.POOL
    npc_couples = [
        couple
        for couple in state.couples
        if "player" not in {couple.partner_a_id, couple.partner_b_id}
    ]
    if flush.player_decision is FlushDecision.RETURN_WITH_ORIGINAL and flush.original_partner_id is not None:
        state.couples = [
            Couple(
                partner_a_id="player",
                partner_b_id=flush.original_partner_id,
                formed_on_day=state.day,
                formed_via="flush_return",
            )
        ] + npc_couples
    elif flush.player_decision is FlushDecision.RETURN_WITH_NEW and flush.chosen_partner_id is not None:
        state.couples = [
            Couple(
                partner_a_id="player",
                partner_b_id=flush.chosen_partner_id,
                formed_on_day=state.day,
                formed_via="flush_return",
            )
        ] + npc_couples
    else:
        state.couples = npc_couples
    for heartbreaker in state.heartbreakers:
        if not heartbreaker.eliminated:
            heartbreaker.location_id = Location.POOL
    flush.returned = True
    event = CeremonyEvent(
        kind="flush_of_hearts_return_reveal",
        message=flush_decision_message(state, flush.player_decision, flush.chosen_partner_id),
        heartbreaker_id=flush.chosen_partner_id or flush.original_partner_id,
    )
    _remember_return(state, event)
    return event


def compute_npc_flush_choices(state: GameState, rng: SeededRng) -> dict[str, str]:
    """Deterministic placeholder choices for NPC Flush outcomes."""
    choices: dict[str, str] = {}
    for heartbreaker in state.heartbreakers:
        if heartbreaker.eliminated or heartbreaker.id == "player":
            continue
        choices[heartbreaker.id] = "twist" if rng.randint(1, 100) <= heartbreaker.relationship.chemistry else "stick"
    return choices


def _ensure_flush_cast(state: GameState) -> list[HeartbreakerState]:
    existing = {heartbreaker.id for heartbreaker in state.heartbreakers}
    cast = []
    for heartbreaker in _flush_cast():
        if heartbreaker.id not in existing:
            state.heartbreakers.append(heartbreaker)
            cast.append(heartbreaker)
        else:
            cast.append(find_heartbreaker(state, heartbreaker.id))
    return cast


def _flush_cast() -> list[HeartbreakerState]:
    index = load_content()
    backstories = index.backstories
    content = index.flush_of_hearts_cast
    return [
        _flush(content["beau"], backstories, 9, "secure", Location.FLUSH_POOL),
        _flush(content["jules"], backstories, 7, "anxious", Location.FLUSH_KITCHEN),
        _flush(content["mateo"], backstories, 10, "avoidant", Location.FLUSH_TERRACE),
        _flush(content["sasha"], backstories, 8, "secure", Location.FLUSH_POOL),
        _flush(content["zara"], backstories, 12, "avoidant", Location.FLUSH_KITCHEN),
        _flush(content["noor"], backstories, 6, "anxious", Location.FLUSH_TERRACE),
    ]


def _flush(
    member: FlushOfHeartsCastContent,
    backstories: dict[str, str],
    chemistry: int,
    attachment: str,
    location: Location,
) -> HeartbreakerState:
    gender = Gender.MAN if member.gender == "m" else Gender.WOMAN
    trait_card = _flush_trait_card(member.id)
    return HeartbreakerState(
        id=member.id,
        name=member.name,
        gender=gender,
        archetype=member.archetype,
        backstory=backstories[member.id],
        location_id=location,
        relationship=RelationshipState(affection=12, chemistry=chemistry),
        public_perception=52,
        big5=Big5(openness=7, conscientiousness=6, extraversion=8, agreeableness=6, neuroticism=5),
        attachment=AttachmentStyle(attachment),
        ideal_match=IdealMatch(
            physical_type="fresh Flush confidence",
            personality_type=["curious", "bold"],
            values=["chemistry", "honesty"],
            dealbreakers=["game playing"],
        ),
        trait_card=trait_card,
    )


def _flush_trait_card(heartbreaker_id: str) -> TraitCard:
    cards = list(heart_throb_trait_cards().values())
    index_by_id = {"beau": 0, "jules": 1, "mateo": 2, "sasha": 3, "zara": 1, "noor": 2}
    return cards[index_by_id.get(heartbreaker_id, 0)]


def _active_flush(state: GameState) -> FlushOfHeartsState:
    if state.flush_of_hearts_state is None:
        raise ValueError("Flush of Hearts is not active")
    return state.flush_of_hearts_state


def _adjust_player_perception(state: GameState, delta: int) -> None:
    state.player.public_perception = clamp_relationship(state.player.public_perception + delta)


def flush_decision_message(
    state: GameState,
    decision: FlushDecision,
    partner_id: str | None,
) -> str:
    if decision is FlushDecision.RETURN_WITH_ORIGINAL:
        return "You chose to return loyal to your original connection."
    if decision is FlushDecision.RETURN_WITH_NEW and partner_id is not None:
        return f"You chose to return with {find_heartbreaker(state, partner_id).name}."
    return "You chose to return solo."


def _remember_return(state: GameState, event: CeremonyEvent) -> None:
    remember_ceremony_events(state, [event])
    for heartbreaker in state.heartbreakers:
        if not heartbreaker.eliminated:
            add_memory(
                state,
                create_memory(
                    holder_id=heartbreaker.id,
                    subject_id="player",
                    source="witnessed",
                    day=state.day,
                    turn=state.turn_index,
                    weight=9,
                    tags=["flush_of_hearts", "return_reveal"],
                    content=event.message,
                    recap_disposition=RecapDisposition.NONE,
                ),
            )
