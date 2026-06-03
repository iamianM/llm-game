"""Narration agents for Blackfen Road."""

from __future__ import annotations

from typing import Protocol

from src.blackfen.content import load_world
from src.blackfen.models import GameState, MechanicalResult, RunStatus


class Narrator(Protocol):
    """Render a resolved mechanical result as player-facing prose."""

    def narrate(self, state: GameState, result: MechanicalResult) -> str:
        """Return narration for an already-resolved turn."""


class MockNarrator:
    """Deterministic narrator for tests and offline play."""

    def narrate(self, state: GameState, result: MechanicalResult) -> str:
        world = load_world()
        location = world.locations[state.current_location_id]
        lines = [result.summary]
        lines.extend(result.details)
        if result.discovered_locations:
            names = [world.locations[id_].name for id_ in result.discovered_locations]
            lines.append("New leads: " + ", ".join(names) + ".")
        if result.items_gained:
            names = [world.items[id_].name for id_ in result.items_gained]
            lines.append("You gain: " + ", ".join(names) + ".")
        if state.status is RunStatus.DEAD:
            lines.append("Your road ends in Blackfen. The next traveler may find what you left behind.")
        elif state.status is RunStatus.VICTORY:
            lines.append("The drowned bell falls silent. Blackfen will remember your name.")
        else:
            lines.append(f"You are at {location.name}. {location.description}")
        return "\n".join(lines)
