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
    """Generate the assembled follow-up wheel from code defaults plus bespoke options.

    The wheel is what the player acts on next, so this must never dead-screen the
    turn. The bespoke-options agent retries on validation failure and then raises
    (every failed attempt is already recorded in the agent trace); that raise — or
    a menu that still fails ``validate_follow_up_menu`` — would otherwise crash the
    whole turn *after the NPC has already spoken*, leaving the player staring at an
    empty fan. On any such failure we degrade to the engine-default wheel (the same
    code-controlled menu test/mock mode uses, which always validates). Only the
    LLM's bespoke flavor is dropped for the turn; the player keeps usable options.
    """
    already_present = already_present_intents(state, result, exchange)
    try:
        raw = _request_contextual_options(
            state, result, exchange, probability, contextual_options, already_present
        )
        menu = _assemble_menu(state, result, exchange, raw)
        validate_follow_up_menu(menu)
        return menu
    except Exception:
        return _default_follow_up_menu(state, result, exchange)


def _request_contextual_options(
    state: GameState,
    result: MechanicalResult,
    exchange: Exchange,
    probability: int,
    contextual_options: ContextualOptionsFn | None,
    already_present: list[str],
) -> ContextualOptionsResult:
    if contextual_options is None:
        # Mock mode: keep the NPC in the conversation by default so test-mode
        # gameplay isn't a one-line dead-end every time. Real-mode contextual
        # options decide departure based on the actual chat context.
        return mock_contextual_bespoke()
    call = cast(Any, contextual_options)
    if "already_present" in inspect.signature(contextual_options).parameters:
        return call(state, result, exchange, probability, already_present=already_present)
    return contextual_options(state, result, exchange, probability)


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
    raise TypeError(f"unknown contextual options result: {type(raw)!r}")


def _default_follow_up_menu(
    state: GameState,
    result: MechanicalResult,
    exchange: Exchange,
) -> FollowUpMenu:
    """Engine-default wheel used when the bespoke agent (or its validation) fails.

    Built only from code-controlled defaults — no LLM flavor — so it always
    validates and the turn never dead-screens. The NPC stays in the conversation
    (``npc_will_leave`` defaults False), exactly like mock mode.
    """
    menu = _assemble_menu(state, result, exchange, mock_contextual_bespoke())
    validate_follow_up_menu(menu)
    return menu
