from typing import Never

from src.game.agents.heartbreaker_voice import Exchange
from src.game.agents.turn_agents import TurnAgentSet, mock_turn_agents
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.rules import MechanicalResult
from src.game.state.models import Mood, new_game


def _unused(*_args: object) -> Never:
    raise AssertionError("contract test callable should not run")


def test_turn_agent_set_is_frozen_and_requires_every_port() -> None:
    agents = TurnAgentSet(
        heartbreaker_voice=_unused,
        contextual_options=_unused,
        event_narrator=_unused,
        conversation_curator=_unused,
        resort_orchestrator=_unused,
        background_dialogue=_unused,
    )

    assert agents.__dataclass_params__.frozen


def test_mock_contextual_options_port_accepts_exact_five_arguments() -> None:
    state = new_game(1)
    result = MechanicalResult(
        action=PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id="chloe",
            intent_id="friendly_chat_resort",
        ),
        success=True,
    )
    exchange = Exchange(
        player_dialogue="Hello.",
        npc_dialogue="Hi.",
        npc_tone="warm",
        npc_mood_after=Mood.CONTENT,
    )

    bespoke = mock_turn_agents().contextual_options(
        state, result, exchange, 20, ["end_softly"]
    )

    assert bespoke.options
