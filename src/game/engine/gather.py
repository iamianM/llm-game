"""Mandatory gather helpers."""

from __future__ import annotations

from collections.abc import Callable

from src.game.agents.conversation_curator import ConversationCuratorFn
from src.game.engine.conversation import close_conversation
from src.game.state.models import Conversation, GameState, MemoryBatch, NPCNPCConversation

PlayerConversationCurator = Callable[[GameState, Conversation, ConversationCuratorFn | None], MemoryBatch]
NPCConversationCurator = Callable[[GameState, NPCNPCConversation, ConversationCuratorFn | None], MemoryBatch]


def close_conversations_for_gather(
    state: GameState,
    curator: ConversationCuratorFn | None,
    curate_conversation: PlayerConversationCurator,
    curate_npc_conversation: NPCConversationCurator,
) -> list[MemoryBatch]:
    """Curate and close every open conversation before a mandatory gather."""
    batches: list[MemoryBatch] = []
    if state.active_conversation is not None:
        batches.append(curate_conversation(state, state.active_conversation, curator))
        close_conversation(state, "gather_event")
    for conversation in list(state.npc_conversations):
        batches.append(curate_npc_conversation(state, conversation, curator))
    state.npc_conversations = []
    return batches


def move_everyone_to_gather(state: GameState) -> None:
    """Move every active islander and the player to the pending gather location."""
    if state.pending_gather is None:
        raise ValueError("cannot move to gather without pending gather")
    location = state.pending_gather.gather_location
    state.location_id = location
    for islander in state.islanders:
        if not islander.eliminated:
            islander.location_id = location
