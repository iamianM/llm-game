"""Pull-for-chat mechanics for contested conversations.

Design sources:
- 09-Social-Dynamics.md: The Pull System
- docs/build-plan-G8.md: Phase G8.2 Pull-for-Chat

Implementation rule:
The engine decides whether a pull succeeds. The Islander Voice may write a
deflection line after a miss, but it does not decide the pull outcome.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.game.engine.memory import add_memory, create_memory
from src.game.state.models import GameState, IslanderState, Location, NPCNPCConversation
from src.game.state.rng import SeededRng


class PullAttempt(BaseModel):
    """One attempt to pull an NPC out of an active NPC-NPC conversation."""

    model_config = ConfigDict(extra="forbid")

    target_id: str
    started_from_location: Location
    success: bool
    chance: int = Field(ge=10, le=90)
    roll: int = Field(ge=1, le=100)
    blocked_conversation_id: str | None = None
    deflection_line: str | None = None


def target_in_active_conversation(
    state: GameState,
    target_id: str,
) -> NPCNPCConversation | None:
    """Return the active NPC-NPC conversation containing ``target_id``."""
    for conversation in state.npc_conversations:
        if conversation.status == "active" and target_id in conversation.participants:
            return conversation
    return None


def pull_chance(state: GameState, target_id: str) -> int:
    """Calculate the chance of successfully pulling a busy NPC for a chat."""
    target = _target(state, target_id)
    privacy_modifier = {
        Location.BEDROOM: 10,
        Location.TERRACE: 5,
        Location.CASA_TERRACE: 5,
        Location.POOL: 0,
        Location.CASA_POOL: 0,
        Location.KITCHEN: -5,
        Location.CASA_KITCHEN: -5,
    }[state.location_id]
    chance = (
        50
        + (state.player.stats.graft * 4)
        + (target.relationship.affection // 4)
        - (target.relationship.chemistry // 3)
        + privacy_modifier
        - (15 * state.player.pull_attempts_this_phase.get(target_id, 0))
    )
    return max(10, min(90, chance))


def attempt_pull(state: GameState, target_id: str, rng: SeededRng) -> PullAttempt:
    """Roll a pull attempt for a target in an active NPC-NPC conversation."""
    blocked = target_in_active_conversation(state, target_id)
    if blocked is None:
        raise ValueError(f"target is not in an active NPC conversation: {target_id}")
    chance = pull_chance(state, target_id)
    roll = rng.randint(1, 100)
    state.player.pull_attempts_this_phase[target_id] = (
        state.player.pull_attempts_this_phase.get(target_id, 0) + 1
    )
    attempt = PullAttempt(
        target_id=target_id,
        started_from_location=state.location_id,
        success=roll <= chance,
        chance=chance,
        roll=roll,
        blocked_conversation_id=blocked.id,
    )
    if not attempt.success:
        _remember_repeated_pull(state, target_id)
    return attempt


def _target(state: GameState, target_id: str) -> IslanderState:
    for islander in state.islanders:
        if islander.id == target_id and not islander.eliminated:
            return islander
    raise ValueError(f"unknown active islander: {target_id}")


def _remember_repeated_pull(state: GameState, target_id: str) -> None:
    if state.player.pull_attempts_this_phase.get(target_id, 0) < 2:
        return
    target = _target(state, target_id)
    if any("player_kept_pulling" in memory.tags for memory in target.memories):
        return
    add_memory(
        state,
        create_memory(
            holder_id=target_id,
            subject_id="player",
            source="direct",
            day=state.day,
            turn=state.turn_index,
            weight=6,
            tags=["player_kept_pulling", "pull"],
            content="Player kept pulling me away today - felt a bit much.",
        ),
    )
