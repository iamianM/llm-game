"""Per-request agent bundle for the Paradise Hearts API."""

from __future__ import annotations

from dataclasses import dataclass

from src.game.agents.background_dialogue import BackgroundDialogueFn, OpenAIBackgroundDialogue
from src.game.agents.contextual_options import ContextualOptionsAgent, ContextualOptionsFn
from src.game.agents.conversation_curator import ConversationCuratorFn, OpenAIConversationCurator
from src.game.agents.event_narrator import EventNarratorFn, OpenAIEventNarrator
from src.game.agents.islander_voice import IslanderVoiceFn, OpenAIIslanderVoice
from src.game.agents.npc_greeter import NpcGreeterFn, OpenAINpcGreeter
from src.game.agents.villa_orchestrator import OpenAIVillaOrchestrator, VillaOrchestratorFn


@dataclass
class AgentBundle:
    """Optional live LLM agent callables, instantiated per request."""

    islander_voice: IslanderVoiceFn | None = None
    contextual_options: ContextualOptionsFn | None = None
    event_narrator: EventNarratorFn | None = None
    conversation_curator: ConversationCuratorFn | None = None
    villa_orchestrator: VillaOrchestratorFn | None = None
    background_dialogue: BackgroundDialogueFn | None = None
    npc_greeter: NpcGreeterFn | None = None

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
            npc_greeter=OpenAINpcGreeter().generate,
        )
