"""Typed capability set passed intact through one game turn."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from src.game.agents.background_dialogue import BackgroundDialogueFn
from src.game.agents.contextual_options import ContextualOptionsResult
from src.game.agents.conversation_curator import ConversationCuratorFn
from src.game.agents.event_narrator import EventNarratorFn
from src.game.agents.heartbreaker_voice import Exchange, HeartbreakerVoiceFn
from src.game.agents.resort_orchestrator import ResortOrchestratorFn
from src.game.engine.rules import MechanicalResult
from src.game.state.models import GameState

TurnContextualOptionsFn = Callable[
    [GameState, MechanicalResult, Exchange, int, list[str]],
    ContextualOptionsResult,
]


@dataclass(frozen=True, slots=True)
class TurnAgentSet:
    """The six required narrative capabilities available during a turn."""

    heartbreaker_voice: HeartbreakerVoiceFn
    contextual_options: TurnContextualOptionsFn
    event_narrator: EventNarratorFn
    conversation_curator: ConversationCuratorFn
    resort_orchestrator: ResortOrchestratorFn
    background_dialogue: BackgroundDialogueFn


__all__ = ["TurnAgentSet", "TurnContextualOptionsFn"]
