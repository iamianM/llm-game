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
    if "supportive" in result.tags and result.success:
        delta = 2
    elif "honest_vulnerable" in result.tags and result.success:
        delta = 1
    elif "escalate_flirt" in result.tags and not result.success:
        delta = -1
    elif "intense" in result.tags and not result.success:
        delta = -2
    elif "flirty" in result.tags and not result.success:
        delta = -1
    state.player.public_perception = clamp_relationship(state.player.public_perception + delta)
