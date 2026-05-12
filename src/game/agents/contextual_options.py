"""Contextual follow-up menu agent.

Design sources:
- 03-LLM-Architecture.md: Dialogue AI
- 11-Conversation-Flow.md: Contextual Follow-up Generation

Implementation rule:
The agent proposes follow-up choices and departure flavor only. Deterministic
engine code validates the menu and resolves mechanics.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict

from src.game.agents.islander_voice import Exchange, load_dotenv_local
from src.game.engine.rules import MechanicalResult
from src.game.state.models import FollowUpMenu, FollowUpOption, GameState

CONTEXTUAL_OPTIONS_MODEL = "gpt-5.4-mini"
EXIT_INTENT_KINDS = {"end_softly", "walk_away", "change_subject_and_drift"}


class ContextualOptionsContext(BaseModel):
    """Visible context for the Contextual Options agent."""

    model_config = ConfigDict(extra="forbid")

    npc_name: str
    npc_archetype: str
    npc_mood: str
    relationship_summary: str
    last_npc_dialogue: str
    last_npc_tone: str
    recent_history: str
    charm: int
    banter: int
    eq: int
    graft: int
    loyalty: int
    departure_probability: int


ContextualOptionsFn = Callable[[GameState, MechanicalResult, Exchange, int], FollowUpMenu]


class ContextualOptionsAgent:
    """Structured follow-up menu generator backed by OpenAI Responses."""

    def __init__(self, *, model: str = CONTEXTUAL_OPTIONS_MODEL) -> None:
        load_dotenv_local()
        self._client = OpenAI()
        self._model = model

    def generate(
        self,
        state: GameState,
        result: MechanicalResult,
        exchange: Exchange,
        departure_probability: int,
    ) -> FollowUpMenu:
        """Generate and validate one contextual follow-up menu."""
        context = contextual_options_context(state, result, exchange, departure_probability)
        rendered = _render_context(context)
        menu = self._generate_menu(rendered)
        try:
            validate_follow_up_menu(menu)
        except ValueError as exc:
            retry = (
                f"{rendered}\n\n"
                "The previous FollowUpMenu failed validation. "
                f"Validation error: {exc}. "
                "Return a corrected FollowUpMenu that satisfies every hard rule."
            )
            menu = self._generate_menu(retry)
            validate_follow_up_menu(menu)
        return menu

    def _generate_menu(self, rendered_context: str) -> FollowUpMenu:
        """Request one parsed menu from the model."""
        response = self._client.responses.parse(
            model=self._model,
            reasoning={"effort": "low"},
            instructions=Path("src/game/agents/prompts/contextual_options.md").read_text(
                encoding="utf-8"
            ),
            input=rendered_context,
            text_format=FollowUpMenu,
            max_output_tokens=520,
        )
        menu = response.output_parsed
        if menu is None:
            raise ValueError("Contextual Options returned no parsed FollowUpMenu")
        return menu


def contextual_options_context(
    state: GameState,
    result: MechanicalResult,
    exchange: Exchange,
    departure_probability: int,
) -> ContextualOptionsContext:
    """Build prompt context for one follow-up menu."""
    target_id = result.action.target_id
    target = next((islander for islander in state.islanders if islander.id == target_id), None)
    if target is None:
        raise ValueError(f"contextual options target not found: {target_id}")
    stats = state.player.stats
    recent_history = "No prior exchanges."
    if state.active_conversation is not None and state.active_conversation.exchanges:
        recent_history = "\n".join(
            f"- player tried {record.intent_id}; NPC tone {record.npc_tone}; success {record.success}"
            for record in state.active_conversation.exchanges[-3:]
        )
    rel = target.relationship
    return ContextualOptionsContext(
        npc_name=target.name,
        npc_archetype=target.archetype,
        npc_mood=target.mood.value,
        relationship_summary=(
            f"affection {rel.affection}, chemistry {rel.chemistry}, "
            f"trust {rel.trust}, friendship {rel.friendship}"
        ),
        last_npc_dialogue=exchange.npc_dialogue,
        last_npc_tone=exchange.npc_tone,
        recent_history=recent_history,
        charm=stats.charm,
        banter=stats.banter,
        eq=stats.eq,
        graft=stats.graft,
        loyalty=stats.loyalty,
        departure_probability=departure_probability,
    )


def mock_follow_up_menu(intent_kind: str = "joke_back", *, npc_will_leave: bool = False) -> FollowUpMenu:
    """Return a deterministic menu that includes ``intent_kind`` for replay."""
    options = [
        FollowUpOption(
            text=f"Follow that thread with {intent_kind.replace('_', ' ')}.",
            intent_kind=intent_kind,
            stat_used="banter",
            risk="medium",
            tone="playful",
        ),
        FollowUpOption(
            text="Let's leave this on a good note.",
            intent_kind="end_softly",
            stat_used=None,
            risk="safe",
            tone="warm",
        ),
    ]
    return FollowUpMenu(
        options=options,
        npc_will_leave=npc_will_leave,
        npc_exit_line="I should go mingle for a bit." if npc_will_leave else None,
    )


def validate_follow_up_menu(menu: FollowUpMenu) -> None:
    """Fail loud if a follow-up menu violates the prompt contract."""
    if not 2 <= len(menu.options) <= 4:
        raise ValueError(f"follow-up option count out of bounds: {len(menu.options)}")
    exit_count = sum(option.intent_kind in EXIT_INTENT_KINDS for option in menu.options)
    if exit_count != 1:
        raise ValueError(f"follow-up menu must contain exactly one exit option: {menu}")
    for option in menu.options:
        if re.search(r"\d", option.text):
            raise ValueError(f"follow-up option contains digits: {option.text!r}")
    if menu.npc_will_leave:
        if not menu.npc_exit_line:
            raise ValueError("npc_exit_line is required when npc_will_leave is true")
        if len(menu.npc_exit_line.split()) > 40:
            raise ValueError(f"npc_exit_line too long: {menu.npc_exit_line!r}")


def _render_context(context: ContextualOptionsContext) -> str:
    return "\n".join(
        [
            f"NPC name: {context.npc_name}",
            f"Archetype voice: {context.npc_archetype}",
            f"Current mood: {context.npc_mood}",
            f"Relationship summary: {context.relationship_summary}",
            f"Last NPC line: {context.last_npc_dialogue}",
            f"Last NPC tone: {context.last_npc_tone}",
            f"Recent exchange history: {context.recent_history}",
            "Player stats:",
            f"charm {context.charm}, banter {context.banter}, eq {context.eq}, "
            f"graft {context.graft}, loyalty {context.loyalty}",
            f"Departure probability: {context.departure_probability}",
            "Write the follow-up menu now.",
        ]
    )
