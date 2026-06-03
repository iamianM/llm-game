"""Seeded RNG boundary for Blackfen Road."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class SeededRng:
    """Small deterministic RNG wrapper for gameplay paths."""

    seed: int | str
    _random: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._random = random.Random(self.seed)

    def randint(self, minimum: int, maximum: int) -> int:
        return self._random.randint(minimum, maximum)

    def choice(self, values: Sequence[T]) -> T:
        if not values:
            raise ValueError("cannot choose from an empty sequence")
        return self._random.choice(values)

    def snapshot(self) -> list[object]:
        version, internalstate, gauss_next = self._random.getstate()
        return [version, list(internalstate), gauss_next]

    @classmethod
    def from_snapshot(cls, seed: int | str, snapshot: list[object]) -> SeededRng:
        rng = cls(seed)
        version, internalstate, gauss_next = snapshot
        rng._random.setstate((version, tuple(internalstate), gauss_next))  # type: ignore[arg-type]
        return rng
