"""LLM contract tests for Player Autopilot."""

from __future__ import annotations

import pytest

from src.game.agents.player_autopilot import OpenAIPlayerAutopilot, validate_policy_decision
from src.game.engine.actions import ActionKind, ActionSpec, PlayerAction, available_actions
from src.game.engine.casa_amor import enter_casa_amor
from src.game.state.casa import CasaDecision
from src.game.state.models import Phase, new_game

pytestmark = pytest.mark.llm


def test_autopilot_picks_from_available_actions() -> None:
    state = new_game(1)
    actions = available_actions(state)

    decision = OpenAIPlayerAutopilot().decide(state, actions, persona="player", recent_history=[])

    validate_policy_decision(decision, len(actions))


def test_autopilot_rationale_not_empty() -> None:
    state = new_game(1)
    actions = available_actions(state)

    decision = OpenAIPlayerAutopilot().decide(state, actions, persona="loyal", recent_history=[])

    assert decision.rationale.strip()


def test_autopilot_confidence_in_enum() -> None:
    state = new_game(1)
    actions = available_actions(state)

    decision = OpenAIPlayerAutopilot().decide(state, actions, persona="chaotic", recent_history=[])

    assert decision.confidence in {"high", "medium", "low"}


def test_autopilot_persona_loyal_picks_loyal_options() -> None:
    state = new_game(1)
    enter_casa_amor(state)
    state.day = 5
    state.phase = Phase.EVENING
    actions = available_actions(state)

    decision = OpenAIPlayerAutopilot().decide(state, actions, persona="loyal", recent_history=[])

    chosen = actions[decision.chosen_action_index].action
    assert chosen.kind is ActionKind.CASA_DECISION
    assert chosen.intent_id == CasaDecision.RETURN_WITH_ORIGINAL.value


def test_autopilot_persona_chaotic_picks_risky_options() -> None:
    state = new_game(1)
    enter_casa_amor(state)
    state.day = 5
    state.phase = Phase.EVENING
    actions = available_actions(state)

    decision = OpenAIPlayerAutopilot().decide(state, actions, persona="chaotic", recent_history=[])

    chosen = actions[decision.chosen_action_index].action
    assert chosen.kind is ActionKind.CASA_DECISION
    assert chosen.intent_id == CasaDecision.RETURN_WITH_NEW.value


def test_autopilot_invalid_index_rejected_and_retried() -> None:
    state = new_game(1)
    actions = [ActionSpec(action=PlayerAction(kind=ActionKind.ADVANCE_PHASE), label="Advance phase")]

    decision = OpenAIPlayerAutopilot().decide(state, actions, persona="loyal", recent_history=[])

    validate_policy_decision(decision, len(actions))
