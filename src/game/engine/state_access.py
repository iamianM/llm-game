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


def player_display_name(state: GameState) -> str:
    """Third-person display name for the human player.

    Engine event messages are surfaced verbatim in static/mock mode, stored as
    memory content, and fed to the Event Narrator, so they must already read in
    display terms. Fall back to a neutral in-world label when the session never
    set a name — never the meta phrase "the player" or second-person "you".
    """
    name = (getattr(state.player, "name", "") or "").strip()
    if name and name.lower() != "you":
        return name
    return "the islander"


def display_name(state: GameState, actor_id: str | None) -> str:
    """Resolve an actor id to a display-safe name.

    This is the single typed point where an engine event producer turns an
    islander id (or the ``"player"`` sentinel) into player-facing text, so a raw
    id never reaches a rendered message, a memory, or the narrator context.
    Unknown ids degrade to a humanized form rather than leaking the raw token —
    a structured lookup, never a regex scrub of finished prose (ENGINEERING R7).
    """
    if actor_id is None:
        return "someone"
    if actor_id == "player":
        return player_display_name(state)
    for islander in state.islanders:
        if islander.id == actor_id:
            return islander.name
    return actor_id.replace("_", " ").strip()


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
