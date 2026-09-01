"""Build one isolated eval turn by replaying reviewed prior turns."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel

from src.game.agents.background_dialogue import BackgroundExchange, mock_background_dialogue
from src.game.agents.contextual_options import ContextualBespoke
from src.game.agents.conversation_curator import CuratableConversation
from src.game.agents.event_narrator import EventNarration
from src.game.agents.heartbreaker_voice import Exchange
from src.game.agents.resort_orchestrator import ResortUpdate, mock_resort_orchestrator
from src.game.agents.turn_agents import TurnAgentSet
from src.game.engine.character_creation import create_character
from src.game.engine.phases import PHASE_BUDGETS
from src.game.engine.rules import MechanicalResult
from src.game.engine.turn import run_turn
from src.game.eval.golden_models import GoldenEvalScenario, GoldenTurnSpec, GoldenTurnTarget
from src.game.state.memory import MemoryBatch
from src.game.state.models import FollowUpOption, GameState, NPCNPCConversation, Phase, new_game
from src.game.state.phase_clock import PhaseClock
from src.game.state.rng import SeededRng

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class IsolatedTurnInput:
    """Canonical state and RNG immediately before one target turn."""

    state: GameState
    rng: SeededRng
    replayed_turn_ids: list[str]


def build_isolated_turn_input(
    scenario: GoldenEvalScenario,
    *,
    target_index: int,
) -> IsolatedTurnInput:
    """Replay only reviewed outputs before ``target_index`` in a fresh game."""
    if target_index < 0 or target_index >= len(scenario.turns):
        raise IndexError(f"target turn index out of range: {target_index}")
    state = new_scenario_state(scenario)
    rng = SeededRng(scenario.seed)
    replayed_turn_ids: list[str] = []
    for prior in scenario.turns[:target_index]:
        apply_turn_arrangements(state, prior)
        replay = _GoldenReplayAgents(
            prior.golden,
            live_resort_life=scenario.live_resort_life,
        )
        run_turn(state, prior.action, rng, replay.agent_set())
        replay.assert_exhausted(prior.id)
        replayed_turn_ids.append(prior.id)
    return IsolatedTurnInput(
        state=state,
        rng=rng,
        replayed_turn_ids=replayed_turn_ids,
    )


def apply_turn_arrangements(state: GameState, turn_spec: GoldenTurnSpec) -> None:
    """Apply the target turn's explicit fixture arrangements."""
    if turn_spec.arrange_player_location is not None:
        state.location_id = turn_spec.arrange_player_location
    for heartbreaker in state.heartbreakers:
        location = turn_spec.arrange_npc_locations.get(heartbreaker.id)
        if location is not None:
            heartbreaker.location_id = location
    if turn_spec.arrange_active_conversation is not None:
        state.active_conversation = turn_spec.arrange_active_conversation.model_copy(deep=True)


def turn_arrangements_payload(turn_spec: GoldenTurnSpec) -> dict[str, object]:
    """Return the authored arrangements safe for review artifacts."""
    payload: dict[str, object] = {}
    if turn_spec.arrange_player_location is not None:
        payload["player_location"] = turn_spec.arrange_player_location.value
    if turn_spec.arrange_npc_locations:
        payload["npc_locations"] = {
            heartbreaker_id: location.value
            for heartbreaker_id, location in turn_spec.arrange_npc_locations.items()
        }
    if turn_spec.arrange_active_conversation is not None:
        conversation = turn_spec.arrange_active_conversation
        active: dict[str, object] = {"target_id": conversation.target_id}
        if conversation.pending_interruption is not None:
            active["pending_interruption"] = conversation.pending_interruption.model_dump(mode="json")
        if conversation.pending_options is not None:
            active["pending_options"] = [
                {
                    "label": option.label,
                    "category": option.category,
                    "intent_kind": option.intent_kind,
                }
                for option in conversation.pending_options.options
            ]
        payload["active_conversation"] = active
    return payload


def new_scenario_state(scenario: GoldenEvalScenario) -> GameState:
    state = new_game(scenario.seed, player_stats=scenario.player_stats)
    intended_phase = scenario.initial_phase
    intended_budget = scenario.initial_phase_budget_minutes
    if scenario.initial_day is not None:
        state.day = scenario.initial_day
    if intended_phase is not None:
        state.phase = intended_phase
        state.phase_clock = PhaseClock(
            phase=intended_phase.value,
            budget_minutes=PHASE_BUDGETS[intended_phase],
        )
    if intended_budget is not None:
        state.phase_clock.budget_minutes = intended_budget
    if scenario.initial_location is not None:
        state.location_id = scenario.initial_location
    if scenario.initial_relationships is not None:
        for heartbreaker in state.heartbreakers:
            relationship = scenario.initial_relationships.get(heartbreaker.id)
            if relationship is not None:
                heartbreaker.relationship = relationship.model_copy(deep=True)
    if scenario.initial_couples is not None:
        state.couples = [couple.model_copy(deep=True) for couple in scenario.initial_couples]
    if scenario.initial_npc_conversations is not None:
        state.npc_conversations = [
            conversation.model_copy(deep=True)
            for conversation in scenario.initial_npc_conversations
        ]
    if scenario.character_creation is not None:
        create_character(
            state,
            archetype_id=scenario.character_creation.archetype_id,
            gender=scenario.character_creation.gender,
            stats=scenario.character_creation.stats,
            rerolled=scenario.character_creation.rerolled,
        )
        first_turn = scenario.turns[0]
        if state.phase is Phase.INTROS and first_turn.action.kind.value != "introduce_to":
            target_phase = intended_phase or Phase.MORNING
            state.phase = target_phase
            state.phase_clock = PhaseClock(
                phase=target_phase.value,
                budget_minutes=intended_budget or PHASE_BUDGETS[target_phase],
            )
            state.intro_completed_ids = [
                heartbreaker.id for heartbreaker in state.heartbreakers if not heartbreaker.eliminated
            ]
            state.intro_memory_created = True
    return state


class _GoldenReplayAgents:
    """Return reviewed calls in order and reject any unreviewed agent call."""

    def __init__(self, target: GoldenTurnTarget, *, live_resort_life: bool) -> None:
        self._calls = list(target.calls)
        self._index = 0
        self._live_resort_life = live_resort_life

    def agent_set(self) -> TurnAgentSet:
        return TurnAgentSet(
            heartbreaker_voice=self.heartbreaker_voice,
            contextual_options=self.contextual_options,
            event_narrator=self.event_narrator,
            conversation_curator=self.conversation_curator,
            resort_orchestrator=self.resort_orchestrator,
            background_dialogue=self.background_dialogue,
        )

    def heartbreaker_voice(self, _state: GameState, _result: MechanicalResult) -> Exchange:
        return self._next("heartbreaker_voice", Exchange)

    def contextual_options(
        self,
        _state: GameState,
        _result: MechanicalResult,
        _exchange: Exchange,
        _departure_probability: int,
        _already_present: list[FollowUpOption],
    ) -> ContextualBespoke:
        return self._next("contextual_options", ContextualBespoke)

    def event_narrator(self, _state: GameState, _events: list[Any]) -> EventNarration:
        return self._next("event_narrator", EventNarration)

    def conversation_curator(
        self,
        _state: GameState,
        _conversation: CuratableConversation,
        _bystander_ids: Sequence[str],
    ) -> MemoryBatch:
        return self._next("conversation_curator", MemoryBatch)

    def resort_orchestrator(self, _state: GameState) -> ResortUpdate:
        if not self._live_resort_life:
            return mock_resort_orchestrator(_state)
        return self._next("resort_orchestrator", ResortUpdate)

    def background_dialogue(
        self,
        _state: GameState,
        _conversation: NPCNPCConversation,
        _nudge: str,
    ) -> BackgroundExchange:
        if not self._live_resort_life:
            return mock_background_dialogue(_state, _conversation, _nudge)
        return self._next("background_dialogue", BackgroundExchange)

    def _next(self, agent: str, model: type[ModelT]) -> ModelT:
        if self._index >= len(self._calls):
            raise ValueError(f"golden replay received unreviewed {agent} call")
        call = self._calls[self._index]
        if call.agent != agent:
            raise ValueError(
                f"golden replay expected {call.agent} call {self._index + 1}, got {agent}"
            )
        if call.output_type != model.__name__:
            raise ValueError(
                f"golden replay expected output type {call.output_type}, got {model.__name__}"
            )
        self._index += 1
        return model.model_validate(call.output)

    def assert_exhausted(self, turn_id: str) -> None:
        if self._index != len(self._calls):
            remaining = [call.agent for call in self._calls[self._index :]]
            raise ValueError(f"golden replay turn {turn_id!r} did not call {remaining!r}")
