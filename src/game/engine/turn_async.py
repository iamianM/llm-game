"""Async turn entry point."""

from __future__ import annotations

import asyncio

from src.game.agents.background_dialogue import BackgroundDialogueFn
from src.game.agents.contextual_options import ContextualOptionsFn
from src.game.agents.conversation_curator import ConversationCuratorFn
from src.game.agents.event_narrator import EventNarratorFn
from src.game.agents.islander_voice import IslanderVoiceFn
from src.game.agents.villa_orchestrator import VillaOrchestratorFn
from src.game.engine.actions import PlayerAction
from src.game.engine.turn import TurnResult, run_turn
from src.game.state.models import GameState
from src.game.state.rng import SeededRng


async def run_turn_async(
    state: GameState,
    action: PlayerAction,
    rng: SeededRng,
    islander_voice: IslanderVoiceFn | None = None,
    contextual_options: ContextualOptionsFn | None = None,
    event_narrator: EventNarratorFn | None = None,
    conversation_curator: ConversationCuratorFn | None = None,
    villa_orchestrator: VillaOrchestratorFn | None = None,
    background_dialogue: BackgroundDialogueFn | None = None,
) -> TurnResult:
    """Run a turn from callers that already own an event loop."""
    return await asyncio.to_thread(
        run_turn,
        state,
        action,
        rng,
        islander_voice,
        contextual_options,
        event_narrator,
        conversation_curator,
        villa_orchestrator,
        background_dialogue,
    )
