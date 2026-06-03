"""Typed state and content contracts for Blackfen Road."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = 1


class Ability(StrEnum):
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"


class IntentKind(StrEnum):
    TRAVEL = "travel"
    INSPECT = "inspect"
    TALK = "talk"
    ATTACK = "attack"
    REST = "rest"
    USE_ITEM = "use_item"
    COMMAND_COMPANION = "command_companion"


class RunStatus(StrEnum):
    ACTIVE = "active"
    VICTORY = "victory"
    DEAD = "dead"


class DamageDice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int = Field(ge=1)
    sides: int = Field(ge=2)
    bonus: int = 0


class ItemDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    kind: Literal["weapon", "armor", "consumable", "quest"]
    description: str
    image: str
    damage: DamageDice | None = None
    armor_bonus: int = 0
    heal: int = 0


class ClassDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    hit_points: int
    armor_class: int
    attack_bonus: int
    damage: DamageDice
    abilities: dict[Ability, int]
    starting_items: list[str]


class MonsterDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    image: str
    hit_points: int
    armor_class: int
    attack_bonus: int
    damage: DamageDice
    morale: int = Field(ge=0, le=20)


class NpcDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    role: str
    image: str
    disposition: str
    knows: list[str]
    dialogue_seed: str


class EncounterDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    monsters: list[str]
    treasure: list[str] = Field(default_factory=list)
    reveal_flags: list[str] = Field(default_factory=list)


class LocationDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    kind: Literal["settlement", "wilderness", "dungeon"]
    image: str
    description: str
    exits: list[str]
    npcs: list[str] = Field(default_factory=list)
    encounter: str | None = None
    secrets: list[str] = Field(default_factory=list)
    reveal_locations: list[str] = Field(default_factory=list)
    required_flag: str | None = None


class WorldDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classes: dict[str, ClassDef]
    items: dict[str, ItemDef]
    monsters: dict[str, MonsterDef]
    npcs: dict[str, NpcDef]
    encounters: dict[str, EncounterDef]
    locations: dict[str, LocationDef]


class CharacterState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    class_id: str
    max_hp: int
    hp: int
    armor_class: int
    attack_bonus: int
    damage: DamageDice
    abilities: dict[Ability, int]
    inventory: list[str]


class CompanionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    max_hp: int
    hp: int
    armor_class: int
    attack_bonus: int
    damage: DamageDice
    loyalty: int = Field(ge=0, le=100)
    stance: Literal["support", "cautious", "aggressive"] = "support"


class MonsterState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    instance_id: str
    hp: int


class Intent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: IntentKind
    raw_text: str
    target_id: str | None = None
    approach: str | None = None


class RollRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    die: int
    modifier: int
    total: int
    target: int | None = None


class MechanicalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    rolls: list[RollRecord] = Field(default_factory=list)
    summary: str
    details: list[str] = Field(default_factory=list)
    damage_to_player: int = 0
    damage_to_companion: int = 0
    damage_to_enemies: int = 0
    discovered_locations: list[str] = Field(default_factory=list)
    discovered_flags: list[str] = Field(default_factory=list)
    items_gained: list[str] = Field(default_factory=list)
    items_lost: list[str] = Field(default_factory=list)
    run_status: RunStatus = RunStatus.ACTIVE


class TurnRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_index: int
    input_hash: str
    raw_text: str
    intent: Intent
    mechanical_result: MechanicalResult
    narration: str
    output_hash: str


class GameState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    seed: int
    turn_index: int = 0
    status: RunStatus = RunStatus.ACTIVE
    current_location_id: str = "blackfen_village"
    known_locations: list[str] = Field(default_factory=lambda: ["blackfen_village", "north_road", "hill_shrine"])
    visited_locations: list[str] = Field(default_factory=lambda: ["blackfen_village"])
    player: CharacterState
    companion: CompanionState
    active_monsters: dict[str, list[MonsterState]] = Field(default_factory=dict)
    resolved_encounters: list[str] = Field(default_factory=list)
    quest_flags: list[str] = Field(default_factory=list)
    journal: list[str] = Field(default_factory=list)
    turns: list[TurnRecord] = Field(default_factory=list)
