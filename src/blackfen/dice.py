"""Dice helpers for deterministic Blackfen Road mechanics."""

from __future__ import annotations

from src.blackfen.models import DamageDice, RollRecord
from src.blackfen.rng import SeededRng


def roll_d20(rng: SeededRng, label: str, modifier: int, target: int | None = None) -> RollRecord:
    die = rng.randint(1, 20)
    return RollRecord(label=label, die=die, modifier=modifier, total=die + modifier, target=target)


def roll_damage(rng: SeededRng, dice: DamageDice) -> int:
    total = dice.bonus
    for _ in range(dice.count):
        total += rng.randint(1, dice.sides)
    return max(1, total)
