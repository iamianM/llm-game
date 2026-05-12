"""Deterministic off-screen NPC simulation.

Design sources:
- 08-Daily-Loop.md: daily progression
- 06-Location-System.md: spatial gameplay
- 09-Social-Dynamics.md: off-screen social movement

NPC simulation remains algorithmic in Phase G. It moves islanders, creates
off-screen social events, and writes memories that can later surface as gossip.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.game.engine.memory import add_memory, create_memory
from src.game.state.models import GameState, IslanderState, Location, clamp_relationship
from src.game.state.rng import SeededRng


class ArchetypeBehavior(BaseModel):
    """Tiny deterministic behavior table for the A1 cast."""

    model_config = ConfigDict(extra="forbid")

    move_propensity: int
    flirt_propensity: int


class OffScreenEvent(BaseModel):
    """A mechanical NPC-NPC or NPC-location event."""

    model_config = ConfigDict(extra="forbid")

    actor_id: str
    target_id: str | None = None
    kind: str
    location: Location


BEHAVIOR = {
    "sweetheart": ArchetypeBehavior(move_propensity=25, flirt_propensity=20),
    "joker": ArchetypeBehavior(move_propensity=45, flirt_propensity=35),
    "friend": ArchetypeBehavior(move_propensity=30, flirt_propensity=15),
}


def simulate_off_screen(state: GameState, rng: SeededRng) -> list[OffScreenEvent]:
    """Run deterministic NPC movement and pairwise off-screen interactions."""
    events: list[OffScreenEvent] = []
    locations = list(Location)

    for islander in state.islanders:
        if islander.eliminated:
            continue
        behavior = BEHAVIOR[islander.archetype]
        if rng.randint(1, 100) <= behavior.move_propensity:
            islander.location_id = _choose_destination(state, islander, locations, rng)
            events.append(
                OffScreenEvent(
                    actor_id=islander.id,
                    kind="move",
                    location=islander.location_id,
                )
            )

    for index, actor in enumerate(state.islanders):
        if actor.eliminated:
            continue
        for target in state.islanders[index + 1 :]:
            if target.eliminated or actor.location_id != target.location_id:
                continue
            event = _interaction_event(actor, target, rng)
            events.append(event)
            _remember_off_screen_event(state, event)

    if not any(event.target_id is not None for event in events):
        fallback_event = _fallback_social_event(state, rng)
        if fallback_event is not None:
            events.append(fallback_event)
            _remember_off_screen_event(state, fallback_event)

    return events


def _choose_destination(
    state: GameState,
    islander: IslanderState,
    locations: list[Location],
    rng: SeededRng,
) -> Location:
    choices = [location for location in locations if location != islander.location_id]
    chemistry = islander.relationship.chemistry
    if chemistry >= 10 and state.location_id != islander.location_id and rng.randint(1, 100) <= chemistry:
        return state.location_id
    return rng.choice(choices)


def _interaction_event(
    actor: IslanderState,
    target: IslanderState,
    rng: SeededRng,
) -> OffScreenEvent:
    actor_roll = rng.randint(1, 100)
    target_roll = rng.randint(1, 100)
    behavior = BEHAVIOR[actor.archetype]
    if actor_roll > 80 and target_roll > 80:
        kind = "drama"
    elif actor_roll <= 12 or target_roll <= 12:
        kind = "argue"
    elif actor_roll <= behavior.flirt_propensity + 20:
        kind = "flirt"
    elif actor_roll + target_roll >= 120:
        kind = "bond"
    else:
        kind = "chat"
    if kind in {"flirt", "drama"}:
        actor.public_perception = clamp_relationship(actor.public_perception + 1)
        target.public_perception = clamp_relationship(target.public_perception + 1)
    if kind == "argue":
        actor.public_perception = clamp_relationship(actor.public_perception - 1)
        target.public_perception = clamp_relationship(target.public_perception - 1)
    return OffScreenEvent(
        actor_id=actor.id,
        target_id=target.id,
        kind=kind,
        location=actor.location_id,
    )


def _fallback_social_event(state: GameState, rng: SeededRng) -> OffScreenEvent | None:
    present = [islander for islander in state.islanders if not islander.eliminated]
    if len(present) < 2:
        return None
    actor = rng.choice(present)
    targets = [islander for islander in present if islander.id != actor.id]
    target = rng.choice(targets)
    return OffScreenEvent(
        actor_id=actor.id,
        target_id=target.id,
        kind="chat",
        location=actor.location_id,
    )


def _remember_off_screen_event(state: GameState, event: OffScreenEvent) -> None:
    if event.target_id is None:
        return
    kind_tags = {
        "chat": ["background", "chat"],
        "flirt": ["background", "flirty"],
        "argue": ["background", "conflict"],
        "bond": ["background", "bond"],
        "drama": ["background", "drama", "gossip"],
    }
    weights = {"chat": 4, "flirt": 5, "argue": 6, "bond": 5, "drama": 9}
    actor_name = _islander_name(state, event.actor_id)
    target_name = _islander_name(state, event.target_id)
    for holder_id, subject_id, other_name in [
        (event.actor_id, event.target_id, target_name),
        (event.target_id, event.actor_id, actor_name),
    ]:
        add_memory(
            state,
            create_memory(
                holder_id=holder_id,
                subject_id=subject_id,
                source="witnessed",
                day=state.day,
                turn=state.turn_index,
                weight=weights[event.kind],
                tags=kind_tags[event.kind],
                content=(
                    f"{other_name} and I had a {event.kind} moment at the "
                    f"{event.location.value} on day {state.day}."
                ),
            ),
        )


def _islander_name(state: GameState, islander_id: str) -> str:
    for islander in state.islanders:
        if islander.id == islander_id:
            return islander.name
    return islander_id
