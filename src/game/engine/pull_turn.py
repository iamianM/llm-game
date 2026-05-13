"""Turn-pipeline helpers for failed pull attempts."""

from __future__ import annotations

from src.game.engine.actions import PlayerAction
from src.game.engine.memory import add_memory, create_memory
from src.game.engine.pull import PullAttempt
from src.game.engine.results import MechanicalResult
from src.game.state.models import GameState, RelationshipDelta, clamp_relationship


def pull_rejected_result(
    state: GameState,
    action: PlayerAction,
    pull_attempt: PullAttempt,
) -> MechanicalResult:
    """Apply the immediate relationship cost for a rejected pull."""
    target = next(islander for islander in state.islanders if islander.id == pull_attempt.target_id)
    delta = RelationshipDelta(affection=-1)
    target.relationship.affection = clamp_relationship(target.relationship.affection + delta.affection)
    return MechanicalResult(
        action=action.model_copy(update={"intent_id": "pull_rejected"}),
        success=False,
        roll=pull_attempt.roll,
        success_chance=pull_attempt.chance,
        relationship_deltas={target.id: delta},
        tags=["pull_rejected"],
        pull_attempt=pull_attempt,
    )


def remember_pull_rejection(state: GameState, pull_attempt: PullAttempt) -> None:
    """Create witness memories when a pull attempt fails publicly."""
    target_name = _name_for_memory(state, pull_attempt.target_id)
    for islander in state.islanders:
        if (
            islander.id != pull_attempt.target_id
            and not islander.eliminated
            and islander.location_id == state.location_id
        ):
            add_memory(
                state,
                create_memory(
                    holder_id=islander.id,
                    subject_id="player",
                    source="witnessed",
                    day=state.day,
                    turn=state.turn_index,
                    weight=6,
                    tags=["saw_pull_rejected", "pull", pull_attempt.target_id],
                    content=f"I saw the player try to pull {target_name} away and get brushed off.",
                ),
            )


def _name_for_memory(state: GameState, islander_id: str) -> str:
    for islander in state.islanders:
        if islander.id == islander_id:
            return islander.name
    return islander_id
