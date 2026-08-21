"""Conversation curation helpers for the turn pipeline."""

from __future__ import annotations

from src.game.agents.conversation_curator import ConversationCuratorFn
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
    curator: ConversationCuratorFn,
) -> MemoryBatch:
    """Curate a closed player conversation exactly once."""
    bump_target_familiarity(state, conversation.target_id, 2)
    bystander_ids = conversation_bystanders(state, conversation.target_id)
    batch = _curate(state, conversation, bystander_ids, curator)
    batch.kind = "player"
    conversation.summary = batch.summary or None
    add_memory_batch(state, batch, day=state.day, turn=state.turn_index)
    propagate_gossip_seeds(state, batch.gossip_seeds, day=state.day, turn=state.turn_index)
    emit_revealed_facts(state, conversation)
    return batch


def curate_npc_conversation(
    state: GameState,
    conversation: NPCNPCConversation,
    curator: ConversationCuratorFn,
) -> MemoryBatch:
    """Curate a closed NPC-NPC conversation."""
    conversation.status = "closed"
    bystander_ids = [
        heartbreaker.id
        for heartbreaker in state.heartbreakers
        if heartbreaker.id not in conversation.participants
        and not heartbreaker.eliminated
        and heartbreaker.location_id == conversation.location_id
    ]
    if state.location_id == conversation.location_id:
        bystander_ids.append("player")
    batch = _curate(state, conversation, bystander_ids, curator)
    batch.kind = "background"
    add_memory_batch(state, batch, day=state.day, turn=state.turn_index)
    propagate_gossip_seeds(state, batch.gossip_seeds, day=state.day, turn=state.turn_index)
    return batch


def _curate(
    state: GameState,
    conversation: Conversation | NPCNPCConversation,
    bystander_ids: list[str],
    curator: ConversationCuratorFn,
) -> MemoryBatch:
    """Curate one closed conversation through the selected turn-agent port."""
    return curator(state, conversation, bystander_ids)


def conversation_bystanders(state: GameState, target_id: str) -> list[str]:
    return [
        heartbreaker.id
        for heartbreaker in state.heartbreakers
        if heartbreaker.id != target_id
        and not heartbreaker.eliminated
        and heartbreaker.location_id == state.location_id
    ]


def bump_target_familiarity(state: GameState, target_id: str, amount: int) -> None:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == target_id:
            apply_familiarity(heartbreaker, amount)
            return


def emit_revealed_facts(state: GameState, conversation: Conversation) -> None:
    """Emit KnownFacts for successful tier-revealing conversation intents."""
    target = next(
        (
            heartbreaker
            for heartbreaker in state.heartbreakers
            if heartbreaker.id == conversation.target_id
        ),
        None,
    )
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
    """Return whether every non-partner starting heartbreaker has been introduced."""
    if state.phase is not Phase.INTROS:
        return False
    partner_ids = {
        other_id
        for couple in state.couples
        for other_id in (couple.partner_a_id, couple.partner_b_id)
        if state.player.id in {couple.partner_a_id, couple.partner_b_id}
        and other_id != state.player.id
    }
    required = {
        heartbreaker.id
        for heartbreaker in state.heartbreakers
        if not heartbreaker.eliminated and heartbreaker.id not in partner_ids
    }
    return required <= set(state.intro_completed_ids)


def intro_memory_batch(state: GameState) -> MemoryBatch:
    """Create the single deterministic memory batch for the Day-1 intro segment."""
    drafts = [
        MemoryDraft(
            holder_id=heartbreaker.id,
            subject_id="player",
            content="I properly met the player during Day One intros and got a real first read.",
            source="direct",
            emotional_weight=4,
            tags=["intro", "day_one"],
        )
        for heartbreaker in state.heartbreakers
        if heartbreaker.id in state.intro_completed_ids
    ]
    return MemoryBatch(
        kind="player",
        memories=drafts[:8],
        summary="The player completed the Day One intro circuit and every non-partner got a first read.",
    )
