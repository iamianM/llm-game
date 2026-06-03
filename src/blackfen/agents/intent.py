"""Intent parsing agents for freeform Blackfen Road input."""

from __future__ import annotations

from typing import Protocol

from src.blackfen.content import load_world
from src.blackfen.models import GameState, Intent, IntentKind


class IntentParser(Protocol):
    """Convert freeform player input into a typed engine intent."""

    def parse(self, state: GameState, text: str) -> Intent:
        """Return a typed intent for the current state."""


class LocalIntentParser:
    """Deterministic parser used by CLI tests, mock API runs, and offline play."""

    def parse(self, state: GameState, text: str) -> Intent:
        raw = text.strip()
        if not raw:
            raise ValueError("enter an action")
        lowered = raw.lower()
        world = load_world()
        visible_locations = [world.locations[id_] for id_ in state.known_locations]
        for location in visible_locations:
            names = {location.id.replace("_", " "), location.name.lower()}
            if any(name in lowered for name in names) and _has_travel_verb(lowered):
                return Intent(kind=IntentKind.TRAVEL, raw_text=raw, target_id=location.id)
        current = world.locations[state.current_location_id]
        for exit_id in current.exits:
            location = world.locations[exit_id]
            if location.name.lower() in lowered or exit_id.replace("_", " ") in lowered:
                return Intent(kind=IntentKind.TRAVEL, raw_text=raw, target_id=exit_id)
        for npc_id in current.npcs:
            npc = world.npcs[npc_id]
            if npc.name.lower() in lowered or npc.role.lower() in lowered:
                return Intent(kind=IntentKind.TALK, raw_text=raw, target_id=npc_id)
        if any(word in lowered for word in ("attack", "fight", "shoot", "stab", "strike", "kill")):
            return Intent(kind=IntentKind.ATTACK, raw_text=raw)
        if any(word in lowered for word in ("rest", "sleep", "camp", "recover")):
            return Intent(kind=IntentKind.REST, raw_text=raw)
        if any(word in lowered for word in ("potion", "drink", "use")):
            return Intent(kind=IntentKind.USE_ITEM, raw_text=raw, target_id="healing_potion")
        if "elian" in lowered or "companion" in lowered:
            return Intent(kind=IntentKind.COMMAND_COMPANION, raw_text=raw, approach=raw)
        if any(word in lowered for word in ("look", "search", "inspect", "investigate", "track", "listen", "read")):
            return Intent(kind=IntentKind.INSPECT, raw_text=raw)
        if any(word in lowered for word in ("talk", "ask", "speak", "question")) and current.npcs:
            return Intent(kind=IntentKind.TALK, raw_text=raw, target_id=current.npcs[0])
        return Intent(kind=IntentKind.INSPECT, raw_text=raw, approach="fallback_inspect")


def _has_travel_verb(text: str) -> bool:
    return any(word in text for word in ("go", "walk", "travel", "head", "leave", "enter", "follow"))
