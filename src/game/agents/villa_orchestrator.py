"""Villa Orchestrator agent for off-screen NPC commitments.

Design sources:
- 09-Social-Dynamics.md: NPC autonomous social life
- 07-Gossip-And-Information.md: Memory-driven gossip substrate

Implementation rule:
The Orchestrator commits structure only. It does not write dialogue and does
not mutate GameState; engine/villa.py validates and applies the commit.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import cached_property
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from src.game.agents.islander_voice import load_dotenv_local
from src.game.agents.runtime import (
    GAME_AGENT_MODEL,
    AgentGenerationError,
    AgentValidationError,
    begin_agent_attempt,
    end_agent_attempt,
    mark_agent_trace_validation_error,
    reasoning_request_kwargs,
    record_agent_trace,
)
from src.game.engine.casa_amor import location_villa
from src.game.state.autonomy import SummonReason
from src.game.state.models import GameState, Location, NPCInterruption

VILLA_ORCHESTRATOR_MODEL = GAME_AGENT_MODEL
# Background villa life — movement / interruption decisions — doesn't need
# the deep chain-of-thought the player-facing dialogue agents do. Default to
# low effort so each turn doesn't carry 15-30s of orchestrator latency.
VILLA_ORCHESTRATOR_REASONING_EFFORT = os.environ.get(
    "LLM_VILLA_ORCHESTRATOR_REASONING_EFFORT", "low"
)
VILLA_ORCHESTRATOR_PROMPT = "src/game/agents/prompts/villa_orchestrator.md"
_VILLA_ORCHESTRATOR_PROMPT_FILE = Path(__file__).parent / "prompts" / "villa_orchestrator.md"


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


class NPCSummon(BaseModel):
    """One NPC pulled out of an active conversation."""

    model_config = ConfigDict(extra="forbid")

    npc_id: str
    from_conversation_id: str
    reason: SummonReason
    target_location: Location


class VillaUpdate(BaseModel):
    """A structured Orchestrator commit for one player turn."""

    model_config = ConfigDict(extra="forbid")

    npc_movements: list[NPCMovement] = Field(default_factory=list)
    conversation_starts: list[NewConversation] = Field(default_factory=list)
    conversation_continues: list[ContinueConversation] = Field(default_factory=list)
    conversation_ends: list[EndConversation] = Field(default_factory=list)
    npc_interruptions: list[NPCInterruption] = Field(default_factory=list)
    npc_summoned_elsewhere: list[NPCSummon] = Field(default_factory=list)


VillaOrchestratorFn = Callable[[GameState], VillaUpdate]


class OpenAIVillaOrchestrator:
    """Structured Villa Orchestrator backed by OpenAI Responses."""

    def __init__(self, *, model: str = VILLA_ORCHESTRATOR_MODEL) -> None:
        load_dotenv_local()
        self._model = model

    @cached_property
    def _client(self) -> OpenAI:
        return OpenAI()

    def decide(self, state: GameState) -> VillaUpdate:
        """Generate one VillaUpdate commit."""
        rendered = _render_context(state)
        last_error: ValueError | None = None
        for attempt in range(3):
            attempt_number = attempt + 1
            retry_context = rendered
            if last_error is not None:
                retry_context = (
                    f"{rendered}\n\n"
                    "The previous VillaUpdate failed deterministic engine validation. "
                    f"Validation error: {last_error}. "
                    "Return a corrected VillaUpdate. If an NPC interrupts this turn, "
                    "do not also move that interrupter away from the player's location. "
                    "If any NPC is in an active NPC-NPC conversation, do not move them "
                    "with npc_movements unless that same conversation is also listed in "
                    "conversation_ends or the NPC is listed in npc_summoned_elsewhere."
                )
            attempt_token = begin_agent_attempt(attempt_number)
            try:
                try:
                    update = self._generate_update(retry_context)
                except Exception as exc:
                    mark_agent_trace_validation_error("villa_orchestrator", attempt_number, exc)
                    last_error = ValueError(str(exc))
                    if attempt == 2:
                        raise AgentGenerationError(str(exc)) from exc
                    continue
            finally:
                end_agent_attempt(attempt_token)
            try:
                from src.game.engine.villa_validation import (
                    normalize_villa_update,
                    validate_villa_update,
                )

                update = normalize_villa_update(state, update)
                validate_villa_update(state, update)
                return update
            except ValueError as exc:
                mark_agent_trace_validation_error("villa_orchestrator", attempt_number, exc)
                last_error = exc
                if attempt == 2:
                    raise AgentValidationError(str(exc)) from exc
        raise AssertionError("unreachable Villa Orchestrator retry state")

    def _generate_update(self, rendered_context: str) -> VillaUpdate:
        """Request one parsed update from the model."""
        response = self._client.responses.parse(
            model=self._model,
            instructions=_VILLA_ORCHESTRATOR_PROMPT_FILE.read_text(encoding="utf-8"),
            input=rendered_context,
            text_format=VillaUpdate,
            **reasoning_request_kwargs(effort=VILLA_ORCHESTRATOR_REASONING_EFFORT),
        )
        update = response.output_parsed
        record_agent_trace(
            agent_name="villa_orchestrator",
            model=self._model,
            prompt_path=VILLA_ORCHESTRATOR_PROMPT,
            response=response,
            output=update,
        )
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
        if not islander.eliminated and location_villa(islander.location_id) is state.villa
    )
    conversations = "\n".join(
        (
            f"- {conversation.id}: participants {', '.join(conversation.participants)}, "
            f"location {conversation.location_id.value}, topic {conversation.topic}, "
            f"exchange_count {len(conversation.exchanges)}, status {conversation.status}"
        )
        for conversation in state.npc_conversations
        if conversation.status == "active" and location_villa(conversation.location_id) is state.villa
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
    locked_participants = _locked_participants(state)
    return "\n".join(
        [
            f"Day: {state.day}",
            f"Phase: {state.phase.value}",
            f"Turn: {state.turn_index}",
            f"Player location: {state.location_id.value}",
            f"Current villa: {state.villa.value}",
            f"Player active conversation target: {active_target}",
            f"Player ambient context: {_ambient_context(state)}",
            f"Player isolation: {_player_isolation(state)}",
            "Player active conversation id: player_active" if state.active_conversation is not None else "",
            f"Player active conversation pending_interruption: {pending_interruption}",
            "Islanders:",
            islanders or "none",
            "Active NPC-NPC conversations:",
            conversations or "none",
            "Engine movement constraints:",
            locked_participants,
            "Write the VillaUpdate now.",
        ]
    )


def _locked_participants(state: GameState) -> str:
    rows = []
    for conversation in state.npc_conversations:
        if conversation.status != "active" or location_villa(conversation.location_id) is not state.villa:
            continue
        rows.append(
            f"- {conversation.id}: {', '.join(conversation.participants)} are locked in conversation. "
            "To move one, end the conversation or use npc_summoned_elsewhere; do not use npc_movements."
        )
    return "\n".join(rows) if rows else "none"


def _player_isolation(state: GameState) -> str:
    visible = [
        islander.id
        for islander in state.islanders
        if not islander.eliminated and islander.location_id is state.location_id
    ]
    if visible:
        return f"not alone; present islanders: {', '.join(visible)}"
    return (
        f"player is alone at {state.location_id.value}. If this has happened recently, "
        "consider moving one available islander toward the player."
    )


def _ambient_context(state: GameState) -> str:
    if state.active_ambient_id is None:
        return "none"
    try:
        from src.game.content.ambient import get_ambient_option

        option = get_ambient_option(state.active_ambient_id)
    except ValueError:
        return state.active_ambient_id
    return (
        f"{option.label} at {option.location.value}; "
        f"npc_encounter_boost {option.npc_encounter_boost}; "
        f"consecutive turns {state.consecutive_ambient_turns}"
    )


def _recent_memories(memories: object) -> str:
    if not isinstance(memories, list) or not memories:
        return "none"
    return " | ".join(getattr(memory, "content", "") for memory in memories)
