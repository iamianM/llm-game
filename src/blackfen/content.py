"""YAML content loading and validation for Blackfen Road."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import cast

import yaml

from src.blackfen.models import WorldDef

ROOT = Path(__file__).resolve().parents[2]
WORLD_PATH = ROOT / "data" / "blackfen" / "world.yaml"


@cache
def load_world(path: Path = WORLD_PATH) -> WorldDef:
    """Load the canonical Blackfen Road world data."""
    if not path.is_file():
        raise FileNotFoundError(f"Blackfen world data not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Blackfen world data must be a YAML mapping")
    world = WorldDef.model_validate(cast(dict[str, object], raw))
    _validate_refs(world)
    return world


def lint_world(path: Path = WORLD_PATH) -> WorldDef:
    """Validate and return world data without relying on the cached instance."""
    load_world.cache_clear()
    return load_world(path)


def _validate_refs(world: WorldDef) -> None:
    for class_def in world.classes.values():
        for item_id in class_def.starting_items:
            if item_id not in world.items:
                raise ValueError(f"class {class_def.id} references unknown item {item_id}")
    for location in world.locations.values():
        for exit_id in location.exits:
            if exit_id not in world.locations:
                raise ValueError(f"location {location.id} references unknown exit {exit_id}")
        for npc_id in location.npcs:
            if npc_id not in world.npcs:
                raise ValueError(f"location {location.id} references unknown npc {npc_id}")
        if location.encounter is not None and location.encounter not in world.encounters:
            raise ValueError(f"location {location.id} references unknown encounter {location.encounter}")
        for reveal_id in location.reveal_locations:
            if reveal_id not in world.locations:
                raise ValueError(f"location {location.id} reveals unknown location {reveal_id}")
    for encounter in world.encounters.values():
        for monster_id in encounter.monsters:
            if monster_id not in world.monsters:
                raise ValueError(f"encounter {encounter.id} references unknown monster {monster_id}")
        for item_id in encounter.treasure:
            if item_id not in world.items:
                raise ValueError(f"encounter {encounter.id} references unknown item {item_id}")
