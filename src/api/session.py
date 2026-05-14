"""In-memory API session storage."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from src.game.agents.background_dialogue import BackgroundDialogueFn, OpenAIBackgroundDialogue
from src.game.agents.contextual_options import ContextualOptionsAgent, ContextualOptionsFn
from src.game.agents.conversation_curator import ConversationCuratorFn, OpenAIConversationCurator
from src.game.agents.event_narrator import EventNarratorFn, OpenAIEventNarrator
from src.game.agents.islander_voice import IslanderVoiceFn, OpenAIIslanderVoice
from src.game.agents.villa_orchestrator import OpenAIVillaOrchestrator, VillaOrchestratorFn
from src.game.state.models import GameState
from src.game.state.rng import SeededRng

MAX_SESSIONS = 32


@dataclass
class AgentBundle:
    """Optional live LLM agent callables for one session."""

    islander_voice: IslanderVoiceFn | None = None
    contextual_options: ContextualOptionsFn | None = None
    event_narrator: EventNarratorFn | None = None
    conversation_curator: ConversationCuratorFn | None = None
    villa_orchestrator: VillaOrchestratorFn | None = None
    background_dialogue: BackgroundDialogueFn | None = None

    @classmethod
    def mock(cls) -> AgentBundle:
        return cls()

    @classmethod
    def live(cls) -> AgentBundle:
        return cls(
            islander_voice=OpenAIIslanderVoice().generate,
            contextual_options=ContextualOptionsAgent().generate,
            event_narrator=OpenAIEventNarrator().narrate,
            conversation_curator=OpenAIConversationCurator().curate,
            villa_orchestrator=OpenAIVillaOrchestrator().decide,
            background_dialogue=OpenAIBackgroundDialogue().generate,
        )


@dataclass
class GameSession:
    session_id: str
    state: GameState
    rng: SeededRng
    agents: AgentBundle
    records: list[dict[str, object]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(UTC))
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


SESSIONS: dict[str, GameSession] = {}


def add_session(state: GameState, rng: SeededRng, agents: AgentBundle) -> GameSession:
    """Store and return a new game session."""
    if len(SESSIONS) >= MAX_SESSIONS:
        oldest = min(SESSIONS.values(), key=lambda item: item.last_accessed)
        SESSIONS.pop(oldest.session_id, None)
    session_id = str(uuid4())
    session = GameSession(session_id=session_id, state=state, rng=rng, agents=agents)
    SESSIONS[session_id] = session
    return session


def get_session(session_id: str) -> GameSession | None:
    session = SESSIONS.get(session_id)
    if session is not None:
        session.last_accessed = datetime.now(UTC)
    return session


def delete_session(session_id: str) -> None:
    SESSIONS.pop(session_id, None)
