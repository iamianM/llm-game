"""Public-perception adjustments."""

from __future__ import annotations

from src.game.engine.actions import PlayerAction
from src.game.engine.results import MechanicalResult
from src.game.state.models import GameState, clamp_relationship


def update_public_perception(
    state: GameState,
    _action: PlayerAction,
    result: MechanicalResult,
) -> None:
    """Apply small deterministic public-perception movement."""
    delta = 0
    reason: str | None = None
    if "supportive" in result.tags and result.success:
        delta = 3
        reason = "they liked the support"
    elif "honest_vulnerable" in result.tags and result.success:
        delta = 2
        reason = "they liked the honesty"
    elif "escalate_flirt" in result.tags and not result.success:
        delta = -2
        reason = "they thought the flirt missed"
    elif "intense" in result.tags and not result.success:
        delta = -2
        reason = "they thought it was too much"
    elif "flirty" in result.tags and not result.success:
        delta = -2
        reason = "they thought the flirt missed"
    elif "ambient_repeat" in result.tags:
        delta = -2
        reason = "they wanted more spark"
    before = state.player.public_perception
    state.player.public_perception = clamp_relationship(state.player.public_perception + delta)
    result.audience_delta = state.player.public_perception - before
    result.audience_reason = reason if result.audience_delta else None
