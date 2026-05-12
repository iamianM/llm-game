"""Narrator agent construction and narration calls.

Design sources:
- 03-LLM-Architecture.md: Dialogue Writing, Event Narration
- 11-Conversation-Flow.md: single exchange generation and continuity

Implementation rule:
The Narrator receives resolved mechanical results and visible context. It does
not mutate game state or decide outcomes.
"""

from __future__ import annotations

from src.game.engine.actions import ActionKind
from src.game.engine.rules import MechanicalResult
from src.game.state.models import GameState


def mock_narration(state: GameState, result: MechanicalResult) -> str:
    """Return deterministic mock narration until the real Narrator is enabled."""
    if result.action.kind is ActionKind.TALK:
        target_id = result.action.target_id or "someone"
        outcome = "lands" if result.success else "falls flat"
        return f"Your chat with {target_id} {outcome} by the {state.location_id}."
    if result.action.kind is ActionKind.FLIRT:
        target_id = result.action.target_id or "someone"
        outcome = "sparks" if result.success else "gets awkward"
        return f"Your flirt with {target_id} {outcome} by the {state.location_id}."
    if result.action.kind is ActionKind.ADVANCE_PHASE:
        return f"The villa moves into {state.phase.value}."
    return "The villa shifts around your choice."
