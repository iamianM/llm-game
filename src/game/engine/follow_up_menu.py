"""Follow-up menu generation bridge for the turn pipeline."""

from __future__ import annotations

import inspect
from typing import Any, cast

from src.game.agents.contextual_options import (
    ContextualBespoke,
    ContextualOptionsFn,
    ContextualOptionsResult,
    mock_contextual_bespoke,
    validate_follow_up_menu,
    with_gossip_options,
)
from src.game.agents.islander_voice import Exchange
from src.game.engine.option_defaults import already_present_intents, assemble_follow_up_menu
from src.game.engine.results import MechanicalResult
from src.game.state.models import FollowUpMenu, GameState


def generate_follow_up_menu(
    state: GameState,
    result: MechanicalResult,
    exchange: Exchange,
    probability: int,
    contextual_options: ContextualOptionsFn | None,
) -> FollowUpMenu:
    """Generate the assembled follow-up wheel from code defaults plus bespoke options."""
    already_present = already_present_intents(state, result, exchange)
    if contextual_options is None:
        # Mock mode: keep the NPC in the conversation by default so test-mode
        # gameplay isn't a one-line dead-end every time. Real-mode contextual
        # options decide departure based on the actual chat context.
        raw: ContextualOptionsResult = mock_contextual_bespoke()
    else:
        call = cast(Any, contextual_options)
        if "already_present" in inspect.signature(contextual_options).parameters:
            raw = call(state, result, exchange, probability, already_present=already_present)
        else:
            raw = contextual_options(state, result, exchange, probability)
    if isinstance(raw, FollowUpMenu):
        menu = with_gossip_options(raw, state)
    elif isinstance(raw, ContextualBespoke):
        menu = with_gossip_options(
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
    else:
        raise TypeError(f"unknown contextual options result: {type(raw)!r}")
    validate_follow_up_menu(menu)
    return menu
