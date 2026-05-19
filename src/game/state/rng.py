"""Seeded RNG boundary for all deterministic randomness.

Design sources:
- docs/decisions/0004-seeded-rng-as-core-primitive.md
- 03-LLM-Architecture.md: Algorithm vs LLM Boundaries

Implementation rule:
Gameplay code should not call ambient randomness directly. Every roll must flow
through this module so a seed plus action script can reproduce a run.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class SeededRng:
    """Small wrapper around Python's RNG for deterministic gameplay paths."""

    seed: int | str
    _random: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize the underlying generator."""
        self._random = random.Random(self.seed)

    def randint(self, minimum: int, maximum: int) -> int:
        """Return an inclusive integer roll."""
        return self._random.randint(minimum, maximum)

    def random(self) -> float:
        """Return the next float in [0.0, 1.0)."""
        return self._random.random()

    def choice(self, values: Sequence[T]) -> T:
        """Return one value from a non-empty sequence."""
        if not values:
            raise ValueError("cannot choose from an empty sequence")
        return self._random.choice(values)

    def fork(self, salt: str) -> SeededRng:
        """Create an independent deterministic stream from the root seed."""
        return SeededRng(f"{self.seed}:{salt}")

    def snapshot(self) -> list[object]:
        """Capture mutable RNG state in JSON-serializable form."""
        version, internalstate, gauss_next = self._random.getstate()
        return [version, list(internalstate), gauss_next]

    @classmethod
    def from_snapshot(cls, seed: int | str, snapshot: list[object]) -> SeededRng:
        """Reconstruct an RNG and restore a previously captured snapshot."""
        rng = cls(seed)
        version, internalstate, gauss_next = snapshot
        rng._random.setstate((version, tuple(internalstate), gauss_next))  # type: ignore[arg-type]
        return rng
