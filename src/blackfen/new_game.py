"""New-run construction for Blackfen Road."""

from __future__ import annotations

from src.blackfen.content import load_world
from src.blackfen.models import CharacterState, CompanionState, GameState


def new_game(seed: int, *, player_name: str = "You", class_id: str = "fighter") -> GameState:
    """Create a deterministic Blackfen Road run."""
    world = load_world()
    if class_id not in world.classes:
        raise ValueError(f"unknown class: {class_id}")
    class_def = world.classes[class_id]
    player = CharacterState(
        id="player",
        name=player_name or "You",
        class_id=class_def.id,
        max_hp=class_def.hit_points,
        hp=class_def.hit_points,
        armor_class=class_def.armor_class,
        attack_bonus=class_def.attack_bonus,
        damage=class_def.damage,
        abilities=class_def.abilities,
        inventory=list(class_def.starting_items),
    )
    companion = CompanionState(
        id="elian_moss",
        name="Elian Moss",
        max_hp=12,
        hp=12,
        armor_class=13,
        attack_bonus=3,
        damage=world.items["mace"].damage or class_def.damage,
        loyalty=42,
    )
    return GameState(seed=seed, player=player, companion=companion)
