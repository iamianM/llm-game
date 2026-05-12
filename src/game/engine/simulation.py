"""Deterministic off-screen NPC simulation.

Design sources:
- 08-Daily-Loop.md: daily progression
- 06-Location-System.md: spatial gameplay
- 09-Social-Dynamics.md: off-screen social movement

NPC simulation is mechanical only in Phase B: it mutates relationship values and
returns traceable events, but it does not narrate.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from src.game.state.models import GameState, Location, clamp_relationship
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
        behavior = BEHAVIOR[islander.archetype]
        if rng.randint(1, 100) <= behavior.move_propensity:
            choices = [location for location in locations if location != islander.location_id]
            islander.location_id = rng.choice(choices)
            events.append(
                OffScreenEvent(
                    actor_id=islander.id,
                    kind="move",
                    location=islander.location_id,
                )
            )

    for index, actor in enumerate(state.islanders):
        for target in state.islanders[index + 1 :]:
            if actor.location_id != target.location_id:
                continue
            behavior = BEHAVIOR[actor.archetype]
            if rng.randint(1, 100) <= behavior.flirt_propensity:
                actor.relationship.chemistry = clamp_relationship(actor.relationship.chemistry + 1)
                target.relationship.chemistry = clamp_relationship(target.relationship.chemistry + 1)
                events.append(
                    OffScreenEvent(
                        actor_id=actor.id,
                        target_id=target.id,
                        kind="npc_chat",
                        location=actor.location_id,
                    )
                )

    return events
