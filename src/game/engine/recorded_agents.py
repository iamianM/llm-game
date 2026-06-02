"""Recorded agent shims for deterministic replay.

Design source:
- docs/build-plan-G.md: Determinism via recorded agent commits

Replay reads typed commits from a trace and never calls live LLM agents.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from src.game.agents.background_dialogue import BackgroundExchange
from src.game.agents.conversation_curator import CuratableConversation
from src.game.agents.event_narrator import EventNarration
from src.game.agents.heartbreaker_voice import Exchange
from src.game.agents.resort_orchestrator import ResortUpdate
from src.game.engine.ceremonies import CeremonyEvent
from src.game.engine.rules import MechanicalResult
from src.game.state.models import FollowUpMenu, GameState, MemoryBatch, NPCNPCConversation


class RecordedAgents:
    """Agent stack that replays commits from one trace record at a time."""

    def __init__(self) -> None:
        self._record: dict[str, Any] | None = None
        self._background_index = 0
        self._curator_index = 0

    def begin_turn(self, record: dict[str, Any]) -> None:
        """Set the trace record used by subsequent agent calls."""
        self._record = record
        self._background_index = 0
        self._curator_index = 0

    def heartbreaker_voice(self, _state: GameState, _result: MechanicalResult) -> Exchange:
        """Replay recorded player/NPC dialogue."""
        value = self._required("exchange")
        if not isinstance(value, dict):
            raise ValueError("recorded exchange must be an object")
        return Exchange.model_validate(value)

    def contextual_options(
        self,
        _state: GameState,
        _result: MechanicalResult,
        _exchange: Exchange,
        _departure_probability: int,
    ) -> FollowUpMenu:
        """Replay recorded follow-up menu."""
        value = self._required("follow_up_menu")
        if not isinstance(value, dict):
            raise ValueError("recorded follow_up_menu must be an object")
        return FollowUpMenu.model_validate(value)

    def event_narrator(
        self,
        _state: GameState,
        _events: list[CeremonyEvent],
    ) -> EventNarration:
        """Replay recorded event narration."""
        value = self._required("event_narration")
        if not isinstance(value, dict):
            raise ValueError("recorded event_narration must be an object")
        return EventNarration.model_validate(value)

    def resort_orchestrator(self, _state: GameState) -> ResortUpdate:
        """Replay recorded ResortUpdate commit."""
        value = self._agent_commits().get("resort_update")
        if not isinstance(value, dict):
            raise ValueError("recorded agent_commits.resort_update must be an object")
        return ResortUpdate.model_validate(value)

    def background_dialogue(
        self,
        _state: GameState,
        _conversation: NPCNPCConversation,
        _nudge: str,
    ) -> BackgroundExchange:
        """Replay recorded background dialogue commits in order."""
        values = self._agent_commits().get("background_dialogues")
        if not isinstance(values, list):
            raise ValueError("recorded background_dialogues must be a list")
        if self._background_index >= len(values):
            raise ValueError("recorded background_dialogues exhausted")
        value = values[self._background_index]
        self._background_index += 1
        if not isinstance(value, dict):
            raise ValueError("recorded background dialogue must be an object")
        return BackgroundExchange.model_validate(value)

    def conversation_curator(
        self,
        _state: GameState,
        _conversation: CuratableConversation,
        _bystander_ids: Sequence[str],
    ) -> MemoryBatch:
        """Replay recorded MemoryBatch commits in order."""
        values = self._agent_commits().get("curator_batches")
        if not isinstance(values, list):
            raise ValueError("recorded curator_batches must be a list")
        if self._curator_index >= len(values):
            raise ValueError("recorded curator_batches exhausted")
        value = values[self._curator_index]
        self._curator_index += 1
        if not isinstance(value, dict):
            raise ValueError("recorded curator batch must be an object")
        return MemoryBatch.model_validate(value)

    def _required(self, key: str) -> object:
        if self._record is None:
            raise ValueError("RecordedAgents.begin_turn was not called")
        value = self._record.get(key)
        if value is None:
            raise ValueError(f"trace record is missing required key: {key}")
        return value

    def _agent_commits(self) -> dict[str, Any]:
        if self._record is None:
            raise ValueError("RecordedAgents.begin_turn was not called")
        commits = self._record.get("agent_commits")
        if not isinstance(commits, dict):
            raise ValueError("trace record is missing agent_commits")
        return commits
