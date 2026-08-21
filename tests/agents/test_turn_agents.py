from typing import Never

from src.game.agents.turn_agents import TurnAgentSet


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
