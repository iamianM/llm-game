"""Shared pytest fixtures.

Design sources:
- docs/decisions/0004-seeded-rng-as-core-primitive.md
- docs/decisions/0007-engine-before-content-before-agents.md
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from src.game.content.loader import load_content
from src.game.content.models import ContentIndex
from src.game.state.rng import SeededRng
from src.game.state.snapshot import load_snapshot, state_hash


@pytest.fixture
def seeded_rng() -> SeededRng:
    """Return the standard deterministic test RNG."""
    return SeededRng(42)


@pytest.fixture
def load_fixture_snapshot() -> Callable[[str], dict[str, Any]]:
    """Return a helper that loads a checked-in snapshot fixture."""

    def _load(path: str) -> dict[str, Any]:
        return load_snapshot(Path(path))

    return _load


@pytest.fixture(scope="session")
def content_index() -> ContentIndex:
    """Load content once for tests that need the full content index."""
    return load_content(Path("content"))


@pytest.fixture
def state_hash_assert() -> Callable[[Any, str], None]:
    """Return a helper for asserting stable state hashes."""

    def _assert(payload: Any, expected: str) -> None:
        assert state_hash(payload) == expected

    return _assert
