"""Opt-in Resort Orchestrator tests for NPC interruption constraints."""

from __future__ import annotations

import pytest

from src.game.agents.resort_orchestrator import OpenAIResortOrchestrator
from src.game.engine.resort import validate_resort_update
from src.game.state.memory import RecapDisposition
from src.game.state.models import Conversation, Location, Memory, NPCInterruption, new_game


@pytest.mark.llm
@pytest.mark.parametrize(
    "state_name",
    [
        "no_active_conversation",
        "active_no_motivation",
        "active_with_pending_interruption",
        "active_jealous_colocated",
        "active_gossip_colocated",
    ],
)
def test_resort_orchestrator_interruption_contracts(state_name: str) -> None:
    """Real Orchestrator output obeys the interruption validation contract."""
    state = _state_for_case(state_name)

    update = OpenAIResortOrchestrator().decide(state)

    validate_resort_update(state, update)


def _state_for_case(state_name: str):
    state = new_game(12)
    for heartbreaker in state.heartbreakers:
        heartbreaker.location_id = Location.POOL
    if state_name == "no_active_conversation":
        return state

    state.active_conversation = Conversation(
        target_id="chloe",
        started_on_turn=3,
        started_on_day=1,
    )
    if state_name == "active_no_motivation":
        state.heartbreakers[1].location_id = Location.KITCHEN
        state.heartbreakers[2].location_id = Location.TERRACE
        return state
    if state_name == "active_with_pending_interruption":
        state.active_conversation.pending_interruption = NPCInterruption(
            interrupter_id="maya",
            reason="jealous",
            urgency="polite",
        )
        return state
    if state_name == "active_jealous_colocated":
        maya = state.heartbreakers[1]
        maya.relationship.affection = 35
        maya.relationship.chemistry = 55
        maya.memories.append(
            Memory(
                id="mem_maya_player_flirt",
                holder_id="maya",
                subject_id="player",
                content="I watched the player flirt with Chloe right after giving me attention.",
                source="witnessed",
                formed_on_day=1,
                formed_on_turn=2,
                emotional_weight=8,
                tags=["jealous", "player_flirted", "witnessed"],
                recap_disposition=RecapDisposition.YOUR_DAY,
            )
        )
        return state
    if state_name == "active_gossip_colocated":
        liam = state.heartbreakers[2]
        liam.memories.append(
            Memory(
                id="mem_liam_chloe_secret",
                holder_id="liam",
                subject_id="chloe",
                content="Chloe admitted she is nervous the player is moving too fast.",
                source="direct",
                formed_on_day=1,
                formed_on_turn=2,
                emotional_weight=7,
                tags=["gossip", "chloe", "relationship_doubt"],
                recap_disposition=RecapDisposition.WHILE_BUSY,
            )
        )
        return state
    raise AssertionError(f"unknown test state: {state_name}")
