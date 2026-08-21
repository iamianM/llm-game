"""Typed capability set passed intact through one game turn."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

from src.game.agents.background_dialogue import (
    BackgroundDialogueFn,
    OpenAIBackgroundDialogue,
    mock_background_dialogue,
)
from src.game.agents.contextual_options import (
    ContextualOptionsAgent,
    ContextualOptionsResult,
    mock_contextual_bespoke,
)
from src.game.agents.conversation_curator import (
    ConversationCuratorFn,
    OpenAIConversationCurator,
    mock_conversation_curator,
)
from src.game.agents.event_narrator import (
    EventNarratorFn,
    OpenAIEventNarrator,
    mock_event_narration,
)
from src.game.agents.heartbreaker_voice import (
    Exchange,
    HeartbreakerVoiceFn,
    OpenAIHeartbreakerVoice,
    mock_heartbreaker_voice,
)
from src.game.agents.recorded import RecordedTurnAgents
from src.game.agents.resort_orchestrator import (
    OpenAIResortOrchestrator,
    ResortOrchestratorFn,
    mock_resort_orchestrator,
)
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


LiveTurnAgentProfile = Literal["full", "no_resort_life"]


def mock_turn_agents() -> TurnAgentSet:
    """Return the deterministic agent set used by tests and mock play."""
    return TurnAgentSet(
        heartbreaker_voice=mock_heartbreaker_voice,
        contextual_options=_mock_contextual_options,
        event_narrator=mock_event_narration,
        conversation_curator=mock_conversation_curator,
        resort_orchestrator=mock_resort_orchestrator,
        background_dialogue=mock_background_dialogue,
    )


def live_turn_agents(profile: LiveTurnAgentProfile = "full") -> TurnAgentSet:
    """Construct one live set, optionally keeping resort life deterministic."""
    agents = TurnAgentSet(
        heartbreaker_voice=OpenAIHeartbreakerVoice().generate,
        contextual_options=ContextualOptionsAgent().generate,
        event_narrator=OpenAIEventNarrator().narrate,
        conversation_curator=OpenAIConversationCurator().curate,
        resort_orchestrator=OpenAIResortOrchestrator().decide,
        background_dialogue=OpenAIBackgroundDialogue().generate,
    )
    if profile == "full":
        return agents
    if profile == "no_resort_life":
        mock = mock_turn_agents()
        return replace(
            agents,
            resort_orchestrator=mock.resort_orchestrator,
            background_dialogue=mock.background_dialogue,
        )
    raise ValueError(f"unknown live turn-agent profile: {profile}")


def recorded_turn_agents(recorded: RecordedTurnAgents) -> TurnAgentSet:
    """Return the typed set exposed by a recorded-turn adapter."""
    return TurnAgentSet(
        heartbreaker_voice=recorded.heartbreaker_voice,
        contextual_options=recorded.contextual_options,
        event_narrator=recorded.event_narrator,
        conversation_curator=recorded.conversation_curator,
        resort_orchestrator=recorded.resort_orchestrator,
        background_dialogue=recorded.background_dialogue,
    )


def scripted_turn_agents(
    contextual_options: TurnContextualOptionsFn,
    resort_orchestrator: ResortOrchestratorFn,
) -> TurnAgentSet:
    """Combine scripted scenario commits with deterministic narrative ports."""
    return replace(
        mock_turn_agents(),
        contextual_options=contextual_options,
        resort_orchestrator=resort_orchestrator,
    )


def _mock_contextual_options(
    _state: GameState,
    _result: MechanicalResult,
    _exchange: Exchange,
    _departure_probability: int,
    _already_present: list[str],
) -> ContextualOptionsResult:
    return mock_contextual_bespoke()


__all__ = [
    "LiveTurnAgentProfile",
    "TurnAgentSet",
    "TurnContextualOptionsFn",
    "live_turn_agents",
    "mock_turn_agents",
    "recorded_turn_agents",
    "scripted_turn_agents",
]
