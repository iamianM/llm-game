"""Visible context assembly for the Contextual Options agent."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.game.agents.heartbreaker_voice_context import Exchange
from src.game.engine.rules import MechanicalResult
from src.game.state.models import FollowUpOption, GameState, Memory


class ExistingFollowUpOption(BaseModel):
    """One deterministic choice already present in the final wheel."""

    model_config = ConfigDict(extra="forbid")

    label: str
    category: str
    intent_kind: str


class ContextualOptionsContext(BaseModel):
    """Visible context for the Contextual Options agent."""

    model_config = ConfigDict(extra="forbid")

    npc_name: str
    npc_archetype: str
    npc_mood: str
    relationship_summary: str
    last_npc_dialogue: str
    last_npc_tone: str
    recent_history: str
    charm: int
    banter: int
    eq: int
    spark: int
    loyalty: int
    departure_probability: int
    gossip_memories: str
    private_chat_context: str = "none"
    explored_threads: str = "None yet — this is fresh ground."
    already_present: list[ExistingFollowUpOption] = Field(default_factory=list)


def contextual_options_context(
    state: GameState,
    result: MechanicalResult,
    exchange: Exchange,
    departure_probability: int,
    *,
    already_present: list[FollowUpOption],
) -> ContextualOptionsContext:
    """Build prompt context from player-visible conversation state."""
    target_id = result.action.target_id
    target = next(
        (heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == target_id),
        None,
    )
    if target is None:
        raise ValueError(f"contextual options target not found: {target_id}")
    stats = state.player.stats
    recent_history = "No prior exchanges."
    if state.active_conversation is not None and state.active_conversation.exchanges:
        recent_history = "\n".join(
            f"- player tried {record.intent_id}; NPC tone {record.npc_tone}; success {record.success}"
            for record in state.active_conversation.exchanges
        )
    rel = target.relationship
    return ContextualOptionsContext(
        npc_name=target.name,
        npc_archetype=target.archetype,
        npc_mood=target.mood.value,
        relationship_summary=(
            f"affection {rel.affection}, chemistry {rel.chemistry}, "
            f"trust {rel.trust}, friendship {rel.friendship}"
        ),
        last_npc_dialogue=exchange.npc_dialogue,
        last_npc_tone=exchange.npc_tone,
        recent_history=recent_history,
        charm=stats.charm,
        banter=stats.banter,
        eq=stats.eq,
        spark=stats.spark,
        loyalty=stats.loyalty,
        departure_probability=departure_probability,
        gossip_memories=_gossip_memory_context(state),
        private_chat_context=_private_chat_context(state, result),
        explored_threads=_explored_threads(state, target.id),
        already_present=[
            ExistingFollowUpOption(
                label=option.label,
                category=option.category,
                intent_kind=option.intent_kind,
            )
            for option in already_present
        ],
    )


def render_context(context: ContextualOptionsContext) -> str:
    """Render the compact, player-visible prompt payload."""
    return "\n".join(
        [
            f"NPC name: {context.npc_name}",
            f"Archetype voice: {context.npc_archetype}",
            f"Current mood: {context.npc_mood}",
            f"Relationship summary: {context.relationship_summary}",
            f"Last NPC line: {context.last_npc_dialogue}",
            f"Last NPC tone: {context.last_npc_tone}",
            f"Recent exchange history: {context.recent_history}",
            "Player stats:",
            f"charm {context.charm}, banter {context.banter}, eq {context.eq}, "
            f"spark {context.spark}, loyalty {context.loyalty}",
            f"Departure probability: {context.departure_probability}",
            "Options already supplied by the engine:",
            *(
                [
                    f"- {option.label} | {option.category} | {option.intent_kind}"
                    for option in context.already_present
                ]
                or ["- none"]
            ),
            f"Gossip-eligible memories: {context.gossip_memories}",
            f"Private chat context: {context.private_chat_context}",
            "Already explored with this Heartbreaker (past chats — do not re-open):\n"
            f"{context.explored_threads}",
            "Write the bespoke follow-up additions now.",
        ]
    )


def _private_chat_context(state: GameState, result: MechanicalResult) -> str:
    attempt = result.private_chat_attempt
    if attempt is None or not attempt.success:
        return "none"
    left_behind = [
        heartbreaker.name
        for heartbreaker in state.heartbreakers
        if heartbreaker.id in attempt.blocked_participants and heartbreaker.id != attempt.target_id
    ]
    names = ", ".join(left_behind) if left_behind else "another conversation"
    return (
        f"The player just pulled this Heartbreaker away from {names}. Keep the next choices "
        "on the new private interaction; do not return to the person or topic left behind."
    )


def _explored_threads(state: GameState, target_id: str) -> str:
    threads = [
        memory.content.strip()
        for memory in state.player.memories
        if memory.subject_id == target_id and memory.content and memory.content.strip()
    ]
    if not threads:
        return "None yet — this is fresh ground."
    return "\n".join(f"- {content}" for content in threads[-5:])


def _gossip_memory_context(state: GameState) -> str:
    conversation = state.active_conversation
    if conversation is None or not conversation.gossip_offers:
        return "None."
    return "\n".join(_memory_line(state, memory) for memory in conversation.gossip_offers)


def _memory_line(state: GameState, memory: Memory) -> str:
    return (
        f"- id {memory.id}; subject {_subject_name(state, memory)}; "
        f"weight {memory.emotional_weight}; tags {', '.join(memory.tags)}; "
        f"content {memory.content}"
    )


def _subject_name(state: GameState, memory: Memory) -> str:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == memory.subject_id:
            return heartbreaker.name
    return memory.subject_id
