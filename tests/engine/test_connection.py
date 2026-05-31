"""Tests for the composite Connection model (score, tier label, shift feedback)."""

from __future__ import annotations

import pytest

from src.game.engine.connection import (
    _TIERS,
    connection_label,
    connection_score,
    connection_tier,
    describe_shift,
)
from src.game.state.models import RelationshipDelta, RelationshipState


def _rel(affection=0, chemistry=0, trust=0, friendship=0) -> RelationshipState:
    return RelationshipState(
        affection=affection, chemistry=chemistry, trust=trust, friendship=friendship
    )


# --- composite score ---------------------------------------------------------


def test_score_is_zero_for_no_bonds() -> None:
    assert connection_score(_rel()) == 0


def test_score_is_one_hundred_when_all_bonds_maxed() -> None:
    # Weights sum to 1.0, so a fully-maxed relationship reads as a perfect 100.
    assert connection_score(_rel(100, 100, 100, 100)) == 100


def test_score_stays_in_range_for_any_inputs() -> None:
    for rel in (_rel(100, 0, 0, 0), _rel(0, 100, 0, 0), _rel(13, 71, 4, 99)):
        score = connection_score(rel)
        assert 0 <= score <= 100


def test_chemistry_and_affection_outweigh_trust_and_friendship() -> None:
    # The blend is romance-leaning: the "do I fancy them" axes should produce a
    # higher composite than the same total spent on the foundational axes.
    romantic = connection_score(_rel(affection=60, chemistry=60))
    platonic = connection_score(_rel(trust=60, friendship=60))
    assert romantic > platonic


# --- tier ladder -------------------------------------------------------------


def test_tier_floor_is_just_met() -> None:
    assert connection_tier(0) == (0, "Just met")
    assert connection_label(5) == "Just met"


def test_tier_ceiling_is_inseparable() -> None:
    index, label = connection_tier(100)
    assert label == "Inseparable"
    assert index == len(_TIERS) - 1


def test_tiers_are_monotonic_in_score() -> None:
    last_index = -1
    for score in range(0, 101):
        index, _ = connection_tier(score)
        assert index >= last_index, f"tier index went backwards at {score}"
        last_index = index


def test_every_tier_boundary_lands_on_its_label() -> None:
    for expected_index, (lower, label) in enumerate(_TIERS):
        index, got = connection_tier(lower)
        assert (index, got) == (expected_index, label)


# --- human-language shift feedback -------------------------------------------


def test_net_zero_delta_yields_no_feedback() -> None:
    assert describe_shift(RelationshipDelta(), "Chloe") is None


def test_positive_chemistry_reads_as_spark() -> None:
    line = describe_shift(RelationshipDelta(chemistry=9), "Chloe")
    assert line is not None
    assert "Chloe" in line
    assert "spark" in line.lower()


def test_negative_trust_reads_as_guard_or_loss() -> None:
    line = describe_shift(RelationshipDelta(trust=-6), "Marcus")
    assert line is not None
    assert "Marcus" in line


def test_dominant_dimension_wins_over_smaller_moves() -> None:
    # Big affection swing dominates a tiny chemistry tick.
    line = describe_shift(RelationshipDelta(affection=10, chemistry=1), "Maya")
    assert line is not None
    assert "into you" in line.lower()  # the "big affection +" phrasing


def test_magnitude_buckets_produce_distinct_lines() -> None:
    small = describe_shift(RelationshipDelta(chemistry=2), "Nia")
    medium = describe_shift(RelationshipDelta(chemistry=5), "Nia")
    big = describe_shift(RelationshipDelta(chemistry=10), "Nia")
    assert small != medium != big
    assert len({small, medium, big}) == 3


def test_shift_lines_carry_no_digits_or_stat_words() -> None:
    # Feedback must read in-world: no numbers, and no pure mechanical stat nouns.
    # "trusts you" / "the friendship with X" are natural, feeling-describing
    # English (a verb, a common noun), not a stat readout, so they are allowed;
    # the bare metric nouns "affection"/"chemistry" never belong in prose.
    banned = ("affection", "chemistry")
    for value in (1, 4, 9, -1, -4, -9):
        for field in ("affection", "chemistry", "trust", "friendship"):
            line = describe_shift(RelationshipDelta(**{field: value}), "Sophie")
            assert line is not None
            assert not any(ch.isdigit() for ch in line)
            assert not any(word in line.lower() for word in banned)


@pytest.mark.parametrize("field", ["affection", "chemistry", "trust", "friendship"])
@pytest.mark.parametrize("sign", [1, -1])
def test_every_dimension_and_sign_has_phrasing(field: str, sign: int) -> None:
    for magnitude in (2, 5, 9):
        line = describe_shift(RelationshipDelta(**{field: sign * magnitude}), "Liam")
        assert line is not None and "Liam" in line
