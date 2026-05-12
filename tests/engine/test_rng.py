"""Tests for deterministic RNG behavior.

Design source:
- docs/decisions/0004-seeded-rng-as-core-primitive.md
"""

from src.game.state.rng import SeededRng


def test_same_seed_produces_same_sequence() -> None:
    """Same seed should produce identical rolls."""
    first = SeededRng(123)
    second = SeededRng(123)

    assert [first.randint(1, 100) for _ in range(10)] == [
        second.randint(1, 100) for _ in range(10)
    ]


def test_forked_streams_are_reproducible_by_salt() -> None:
    """Forked streams with the same salt should be reproducible."""
    root = SeededRng(123)

    first = root.fork("npc-behavior")
    second = root.fork("npc-behavior")

    assert [first.randint(1, 100) for _ in range(10)] == [
        second.randint(1, 100) for _ in range(10)
    ]


def test_choice_rejects_empty_sequence() -> None:
    """Choosing from an empty sequence should fail loudly."""
    rng = SeededRng(123)

    try:
        rng.choice([])
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("empty choice did not raise")
