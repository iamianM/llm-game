"""Villa Orchestrator agent for off-screen NPC commitments.

Design sources:
- 09-Social-Dynamics.md: NPC autonomous social life
- 07-Gossip-And-Information.md: Memory-driven gossip substrate

Implementation rule:
The Orchestrator commits structure only. It does not write dialogue and does
not mutate GameState; engine/villa.py validates and applies the commit.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from src.game.agents.islander_voice import load_dotenv_local
from src.game.state.models import GameState, Location, NPCInterruption

VILLA_ORCHESTRATOR_MODEL = "gpt-5.4-mini"


class NPCMovement(BaseModel):
    """One NPC movement proposed by the Orchestrator."""

    model_config = ConfigDict(extra="forbid")

    npc_id: str
    target_location: Location
    reason: str


class NewConversation(BaseModel):
    """One new NPC-NPC conversation proposed by the Orchestrator."""

    model_config = ConfigDict(extra="forbid")

    participants: list[str] = Field(min_length=2, max_length=2)
    location: Location
    topic: str


class ContinueConversation(BaseModel):
    """One active NPC-NPC conversation that should continue."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    nudge: str = ""


class EndConversation(BaseModel):
    """One active NPC-NPC conversation that should close."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    reason: str


class VillaUpdate(BaseModel):
    """A structured Orchestrator commit for one player turn."""

    model_config = ConfigDict(extra="forbid")

    npc_movements: list[NPCMovement] = Field(default_factory=list)
    conversation_starts: list[NewConversation] = Field(default_factory=list)
    conversation_continues: list[ContinueConversation] = Field(default_factory=list)
    conversation_ends: list[EndConversation] = Field(default_factory=list)
    npc_interruptions: list[NPCInterruption] = Field(default_factory=list)


VillaOrchestratorFn = Callable[[GameState], VillaUpdate]


class OpenAIVillaOrchestrator:
    """Structured Villa Orchestrator backed by OpenAI Responses."""

    def __init__(self, *, model: str = VILLA_ORCHESTRATOR_MODEL) -> None:
        load_dotenv_local()
        self._client = OpenAI()
        self._model = model

    def decide(self, state: GameState) -> VillaUpdate:
        """Generate one VillaUpdate commit."""
        response = self._client.responses.parse(
            model=self._model,
            reasoning={"effort": "low"},
            instructions=Path("src/game/agents/prompts/villa_orchestrator.md").read_text(
                encoding="utf-8"
            ),
            input=_render_context(state),
            text_format=VillaUpdate,
            max_output_tokens=900,
        )
        update = response.output_parsed
        if update is None:
            raise ValueError("Villa Orchestrator returned no parsed VillaUpdate")
        return update


def mock_villa_orchestrator(_state: GameState) -> VillaUpdate:
    """Return an empty deterministic update for offline tests."""
    return VillaUpdate()


def _render_context(state: GameState) -> str:
    islanders = "\n".join(
        (
            f"- {islander.id}: {islander.name}, {islander.archetype}, "
            f"location {islander.location_id.value}, mood {islander.mood.value}, "
            f"relationship with player affection {islander.relationship.affection}, "
            f"chemistry {islander.relationship.chemistry}, trust {islander.relationship.trust}; "
            f"recent memories: {_recent_memories(islander.memories)}"
        )
        for islander in state.islanders
        if not islander.eliminated
    )
    conversations = "\n".join(
        (
            f"- {conversation.id}: participants {', '.join(conversation.participants)}, "
            f"location {conversation.location_id.value}, topic {conversation.topic}, "
            f"exchange_count {len(conversation.exchanges)}, status {conversation.status}"
        )
        for conversation in state.npc_conversations
        if conversation.status == "active"
    )
    active_target = (
        "none"
        if state.active_conversation is None
        else state.active_conversation.target_id
    )
    pending_interruption = (
        "none"
        if state.active_conversation is None or state.active_conversation.pending_interruption is None
        else state.active_conversation.pending_interruption.model_dump_json()
    )
    return "\n".join(
        [
            f"Day: {state.day}",
            f"Phase: {state.phase.value}",
            f"Turn: {state.turn_index}",
            f"Player location: {state.location_id.value}",
            f"Player active conversation target: {active_target}",
            f"Player active conversation pending_interruption: {pending_interruption}",
            "Islanders:",
            islanders or "none",
            "Active NPC-NPC conversations:",
            conversations or "none",
            "Write the VillaUpdate now.",
        ]
    )


def _recent_memories(memories: object) -> str:
    if not isinstance(memories, list) or not memories:
        return "none"
    return " | ".join(getattr(memory, "content", "") for memory in memories[-3:])
