"""Small helpers for canonical state mutation."""

from __future__ import annotations

from src.game.state.models import GameState, IslanderState, RelationshipDelta, clamp_relationship


def find_islander(state: GameState, target_id: str | None) -> IslanderState:
    """Return an Islander by id, failing loud on unknown targets."""
    if target_id is None:
        raise ValueError("target_id is required")
    for islander in state.islanders:
        if islander.id == target_id:
            return islander
    raise ValueError(f"unknown islander: {target_id}")


def apply_relationship_delta(target: IslanderState, delta: RelationshipDelta) -> None:
    """Apply a clamped relationship delta to one islander."""
    target.relationship.affection = clamp_relationship(
        target.relationship.affection + delta.affection
    )
    target.relationship.chemistry = clamp_relationship(
        target.relationship.chemistry + delta.chemistry
    )
    target.relationship.trust = clamp_relationship(target.relationship.trust + delta.trust)
    target.relationship.friendship = clamp_relationship(
        target.relationship.friendship + delta.friendship
    )
