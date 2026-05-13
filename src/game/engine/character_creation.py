"""Character creation rules."""

from __future__ import annotations

from dataclasses import dataclass

from src.game.engine.state_access import apply_relationship_delta, find_islander
from src.game.state.models import CharacterCreation, GameState, PlayerStats, RelationshipDelta


@dataclass(frozen=True)
class PlayerArchetypeDef:
    """Deterministic mechanical definition of a player archetype."""

    id: str
    display_name: str
    stat_bonus_name: str
    stat_bonus_value: int
    starter_advantage: str


PLAYER_ARCHETYPES: dict[str, PlayerArchetypeDef] = {
    "heartthrob": PlayerArchetypeDef(
        id="heartthrob",
        display_name="Heartthrob",
        stat_bonus_name="charm",
        stat_bonus_value=3,
        starter_advantage="starter_chemistry",
    ),
    "class_clown": PlayerArchetypeDef(
        id="class_clown",
        display_name="Class Clown",
        stat_bonus_name="banter",
        stat_bonus_value=3,
        starter_advantage="public_perception_boost",
    ),
    "loyal_friend": PlayerArchetypeDef(
        id="loyal_friend",
        display_name="Loyal Friend",
        stat_bonus_name="loyalty",
        stat_bonus_value=3,
        starter_advantage="starter_friendship",
    ),
}

DEFAULT_ARCHETYPE_STATS: dict[str, PlayerStats] = {
    "heartthrob": PlayerStats(charm=9, banter=6, eq=5, graft=5, loyalty=5),
    "class_clown": PlayerStats(charm=5, banter=9, eq=6, graft=5, loyalty=5),
    "loyal_friend": PlayerStats(charm=5, banter=6, eq=5, graft=5, loyalty=9),
}


def create_character(
    state: GameState,
    *,
    archetype_id: str,
    stats: PlayerStats,
    rerolled: bool = False,
) -> CharacterCreation:
    """Apply character creation to the starting player state."""
    if state.turn_index != 0:
        raise ValueError("character creation is only valid before the run starts")
    if state.character_creation is not None:
        raise ValueError("character has already been created")
    if archetype_id not in PLAYER_ARCHETYPES:
        raise ValueError(f"unknown player archetype: {archetype_id}")
    if sum(stats.model_dump().values()) != 30:
        raise ValueError("created character stats must total exactly 30")
    definition = PLAYER_ARCHETYPES[archetype_id]
    bonus_value = getattr(stats, definition.stat_bonus_name)
    if bonus_value < 3 + definition.stat_bonus_value:
        raise ValueError("created stats must include the archetype stat bonus")
    creation = CharacterCreation(archetype_id=archetype_id, stats=stats, rerolled=rerolled)
    state.player.stats = stats
    state.player.archetype_id = archetype_id
    state.player.character_created = True
    state.player.reroll_used = rerolled
    state.character_creation = creation
    _apply_starter_advantage(state, definition)
    return creation


def reroll_character(state: GameState) -> None:
    """Mark the one allowed character reroll as used and reset creation."""
    if state.player.reroll_used:
        raise ValueError("character reroll has already been used")
    state.player.reroll_used = True
    state.character_creation = None


def _apply_starter_advantage(state: GameState, definition: PlayerArchetypeDef) -> None:
    if definition.starter_advantage == "starter_chemistry":
        target = find_islander(state, "chloe")
        apply_relationship_delta(target, RelationshipDelta(chemistry=5))
        return
    if definition.starter_advantage == "public_perception_boost":
        state.player.public_perception = 60
        return
    if definition.starter_advantage == "starter_friendship":
        for islander in state.islanders:
            apply_relationship_delta(islander, RelationshipDelta(friendship=5))
        return
    raise ValueError(f"unknown starter advantage: {definition.starter_advantage}")
