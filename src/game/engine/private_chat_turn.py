"""Turn-pipeline helpers for failed private chat attempts."""

from __future__ import annotations

from src.game.engine.actions import PlayerAction
from src.game.engine.memory import add_memory, create_memory
from src.game.engine.private_chat import PrivateChatAttempt
from src.game.engine.results import MechanicalResult
from src.game.state.models import GameState, RelationshipDelta, clamp_relationship


def private_chat_rejected_result(
    state: GameState,
    action: PlayerAction,
    private_chat_attempt: PrivateChatAttempt,
) -> MechanicalResult:
    """Apply the immediate relationship cost for a rejected private chat."""
    target = next(heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == private_chat_attempt.target_id)
    delta = RelationshipDelta(affection=-1)
    target.relationship.affection = clamp_relationship(target.relationship.affection + delta.affection)
    return MechanicalResult(
        action=action.model_copy(update={"intent_id": "private_chat_rejected"}),
        success=False,
        roll=private_chat_attempt.roll,
        success_chance=private_chat_attempt.chance,
        relationship_deltas={target.id: delta},
        tags=["private_chat_rejected"],
        private_chat_attempt=private_chat_attempt,
    )


def remember_private_chat_rejection(state: GameState, private_chat_attempt: PrivateChatAttempt) -> None:
    """Create witness memories when a private chat attempt fails publicly."""
    target_name = _name_for_memory(state, private_chat_attempt.target_id)
    for heartbreaker in state.heartbreakers:
        if (
            heartbreaker.id != private_chat_attempt.target_id
            and not heartbreaker.eliminated
            and heartbreaker.location_id == state.location_id
        ):
            add_memory(
                state,
                create_memory(
                    holder_id=heartbreaker.id,
                    subject_id="player",
                    source="witnessed",
                    day=state.day,
                    turn=state.turn_index,
                    weight=6,
                    tags=["saw_private_chat_rejected", "private_chat", private_chat_attempt.target_id],
                    content=f"I saw the player ask {target_name} for a private chat and get brushed off.",
                ),
            )


def _name_for_memory(state: GameState, heartbreaker_id: str) -> str:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == heartbreaker_id:
            return heartbreaker.name
    return heartbreaker_id
