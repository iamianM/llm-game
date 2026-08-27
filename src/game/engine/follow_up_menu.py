"""Follow-up menu generation bridge for the turn pipeline."""

from __future__ import annotations

from src.game.agents.contextual_options import (
    ContextualBespoke,
    ContextualOptionsFn,
    ContextualOptionsResult,
    validate_follow_up_menu,
    with_gossip_options,
)
from src.game.agents.heartbreaker_voice import Exchange
from src.game.agents.runtime import AgentValidationError
from src.game.engine.option_defaults import already_present_options, assemble_follow_up_menu
from src.game.engine.results import MechanicalResult
from src.game.state.models import FollowUpMenu, GameState


def generate_follow_up_menu(
    state: GameState,
    result: MechanicalResult,
    exchange: Exchange,
    probability: int,
    contextual_options: ContextualOptionsFn,
) -> FollowUpMenu:
    """Generate and validate the wheel from defaults plus bespoke options."""
    already_present = already_present_options(state, result, exchange)
    raw = contextual_options(state, result, exchange, probability, already_present)
    menu = _assemble_menu(state, result, exchange, raw)
    try:
        validate_follow_up_menu(menu)
    except ValueError as exc:
        raise AgentValidationError(str(exc)) from exc
    return menu


def _assemble_menu(
    state: GameState,
    result: MechanicalResult,
    exchange: Exchange,
    raw: ContextualOptionsResult,
) -> FollowUpMenu:
    if isinstance(raw, FollowUpMenu):
        return with_gossip_options(raw, state)
    if isinstance(raw, ContextualBespoke):
        return with_gossip_options(
            assemble_follow_up_menu(
                state,
                result,
                exchange,
                raw.options,
                npc_will_leave=raw.npc_will_leave,
                npc_exit_line=raw.npc_exit_line,
            ),
            state,
        )
    # The only producers of `raw` are typed turn-agent ports.
    raise AgentValidationError(f"unknown contextual options result: {type(raw)!r}")
