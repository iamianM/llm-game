"""Conversation curation helpers for the turn pipeline."""

from __future__ import annotations

from src.game.agents.conversation_curator import ConversationCuratorFn, mock_conversation_curator
from src.game.engine.compatibility import apply_familiarity
from src.game.engine.intents import get_intent
from src.game.engine.knowledge import emit_fact_reveal, emit_fact_reveal_by_tier
from src.game.engine.memory import add_memory_batch, propagate_gossip_seeds
from src.game.state.models import (
    Conversation,
    GameState,
    MemoryBatch,
    MemoryDraft,
    NPCNPCConversation,
    Phase,
)


def curate_player_conversation(
    state: GameState,
    conversation: Conversation,
    curator: ConversationCuratorFn | None,
) -> MemoryBatch:
    """Curate a closed player conversation exactly once."""
    bump_target_familiarity(state, conversation.target_id, 2)
    bystander_ids = conversation_bystanders(state, conversation.target_id)
    curate = mock_conversation_curator if curator is None else curator
    batch = curate(state, conversation, bystander_ids)
    batch.kind = "player"
    conversation.summary = batch.summary or None
    add_memory_batch(state, batch, day=state.day, turn=state.turn_index)
    propagate_gossip_seeds(state, batch.gossip_seeds, day=state.day, turn=state.turn_index)
    emit_revealed_facts(state, conversation)
    return batch


def curate_npc_conversation(
    state: GameState,
    conversation: NPCNPCConversation,
    curator: ConversationCuratorFn | None,
) -> MemoryBatch:
    """Curate a closed NPC-NPC conversation."""
    conversation.status = "closed"
    bystander_ids = [
        islander.id
        for islander in state.islanders
        if islander.id not in conversation.participants
        and not islander.eliminated
        and islander.location_id == conversation.location_id
    ]
    if state.location_id == conversation.location_id:
        bystander_ids.append("player")
    curate = mock_conversation_curator if curator is None else curator
    batch = curate(state, conversation, bystander_ids)
    batch.kind = "background"
    add_memory_batch(state, batch, day=state.day, turn=state.turn_index)
    propagate_gossip_seeds(state, batch.gossip_seeds, day=state.day, turn=state.turn_index)
    return batch


def conversation_bystanders(state: GameState, target_id: str) -> list[str]:
    return [
        islander.id
        for islander in state.islanders
        if islander.id != target_id
        and not islander.eliminated
        and islander.location_id == state.location_id
    ]


def bump_target_familiarity(state: GameState, target_id: str, amount: int) -> None:
    for islander in state.islanders:
        if islander.id == target_id:
            apply_familiarity(islander, amount)
            return


def emit_revealed_facts(state: GameState, conversation: Conversation) -> None:
    """Emit KnownFacts for successful tier-revealing conversation intents."""
    target = next((islander for islander in state.islanders if islander.id == conversation.target_id), None)
    if target is None:
        return
    for exchange in conversation.exchanges:
        if not exchange.success:
            continue
        try:
            intent = get_intent(exchange.intent_id)
        except ValueError:
            if exchange.intent_id == "go_deeper":
                emit_fact_reveal_by_tier(state, target, 3)
            elif exchange.intent_id == "honest_vulnerable":
                emit_fact_reveal_by_tier(state, target, 3)
            continue
        emit_fact_reveal(state, target, intent)


def intro_segment_complete(state: GameState) -> bool:
    """Return whether every non-partner starting islander has been introduced."""
    if state.phase is not Phase.INTROS:
        return False
    partner_ids = {
        other_id
        for couple in state.couples
        for other_id in (couple.partner_a_id, couple.partner_b_id)
        if state.player.id in {couple.partner_a_id, couple.partner_b_id} and other_id != state.player.id
    }
    required = {
        islander.id
        for islander in state.islanders
        if not islander.eliminated and islander.id not in partner_ids
    }
    return required <= set(state.intro_completed_ids)


def intro_memory_batch(state: GameState) -> MemoryBatch:
    """Create the single deterministic memory batch for the Day-1 intro segment."""
    drafts = [
        MemoryDraft(
            holder_id=islander.id,
            subject_id="player",
            content="I properly met the player during Day One intros and got a real first read.",
            source="direct",
            emotional_weight=4,
            tags=["intro", "day_one"],
        )
        for islander in state.islanders
        if islander.id in state.intro_completed_ids
    ]
    return MemoryBatch(
        kind="player",
        memories=drafts[:8],
        summary="The player completed the Day One intro circuit and every non-partner got a first read.",
    )
