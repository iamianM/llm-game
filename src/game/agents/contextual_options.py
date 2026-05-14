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
from functools import cached_property
from pathlib import Path
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from src.game.agents.islander_voice import Exchange, load_dotenv_local
from src.game.engine.rules import MechanicalResult
from src.game.state.models import FollowUpMenu, FollowUpOption, GameState, Memory

CONTEXTUAL_OPTIONS_MODEL = "gpt-4.1-mini"
EXIT_INTENT_KINDS = {"end_softly", "walk_away", "change_subject_and_drift"}
FOLLOW_UP_CATEGORIES = {
    "friendly",
    "flirty",
    "deep",
    "banter",
    "gossip",
    "supportive",
    "bromance",
    "gossip_ring",
    "exit",
}
BESPOKE_LABEL_MAX_WORDS = 8
ALLOWED_BESPOKE_INTENTS = {
    "honest_vulnerable", "escalate_flirt", "deflect_with_humor", "joke_back",
    "go_deeper", "ask_about_topic", "apologize", "defend_self", "change_subject",
    "supportive_listen", "supportive_comfort", "supportive_reassure", "supportive_validate",
}
FollowUpCategory = Literal["friendly", "flirty", "deep", "banter", "gossip", "supportive", "exit"]


class ContextualOptionsContext(BaseModel):
    """Visible context for the Contextual Options agent."""

    model_config = ConfigDict(extra="forbid")

    npc_name: str
    npc_archetype: str
    npc_backstory: str
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
    gossip_memories: str
    already_present: list[str] = Field(default_factory=list)


class ContextualBespoke(BaseModel):
    """Moment-specific additions to a partially-built follow-up wheel."""

    model_config = ConfigDict(extra="forbid")

    options: list[FollowUpOption] = Field(min_length=1, max_length=2)
    npc_will_leave: bool
    npc_exit_line: str | None = None


ContextualOptionsResult = ContextualBespoke | FollowUpMenu
ContextualOptionsFn = Callable[[GameState, MechanicalResult, Exchange, int], ContextualOptionsResult]


class ContextualOptionsAgent:
    """Structured follow-up menu generator backed by OpenAI Responses."""

    def __init__(self, *, model: str = CONTEXTUAL_OPTIONS_MODEL) -> None:
        load_dotenv_local()
        self._model = model

    @cached_property
    def _client(self) -> OpenAI:
        return OpenAI()

    def generate(
        self,
        state: GameState,
        result: MechanicalResult,
        exchange: Exchange,
        departure_probability: int,
        already_present: list[str] | None = None,
    ) -> ContextualBespoke:
        """Generate and validate bespoke contextual additions."""
        context = contextual_options_context(
            state,
            result,
            exchange,
            departure_probability,
            already_present=already_present or [],
        )
        rendered = _render_context(context)
        last_error: ValueError | None = None
        for attempt in range(3):
            retry_context = rendered
            if last_error is not None:
                retry_context = (
                    f"{rendered}\n\n"
                    "The previous ContextualBespoke failed validation. "
                    f"Validation error: {last_error}. "
                    "Return a corrected ContextualBespoke with one or two specific options "
                    "that do not duplicate already_present."
                )
            bespoke = self._generate_bespoke(retry_context)
            try:
                validate_contextual_bespoke(bespoke, context.already_present)
                return bespoke
            except ValueError as exc:
                last_error = exc
                if attempt == 2:
                    raise
        raise AssertionError("unreachable contextual options retry state")

    def _generate_bespoke(self, rendered_context: str) -> ContextualBespoke:
        """Request one parsed bespoke option set from the model."""
        response = self._client.responses.parse(
            model=self._model,
            instructions=Path("src/game/agents/prompts/contextual_options.md").read_text(
                encoding="utf-8"
            ),
            input=rendered_context,
            text_format=ContextualBespoke,
            max_output_tokens=360,
        )
        bespoke = response.output_parsed
        if bespoke is None:
            raise ValueError("Contextual Options returned no parsed ContextualBespoke")
        return bespoke

def contextual_options_context(
    state: GameState,
    result: MechanicalResult,
    exchange: Exchange,
    departure_probability: int,
    *,
    already_present: list[str] | None = None,
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
        npc_backstory=target.backstory,
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
        gossip_memories=_gossip_memory_context(state),
        already_present=already_present or [],
    )

def mock_contextual_bespoke(
    intent_kind: str = "joke_back",
    *,
    npc_will_leave: bool = False,
) -> ContextualBespoke:
    """Return deterministic bespoke additions for tests and replay."""
    primary_intent = "joke_back" if intent_kind in EXIT_INTENT_KINDS else intent_kind
    return ContextualBespoke(
        options=[
            FollowUpOption(
                label=_mock_label(primary_intent),
                category=_mock_category(primary_intent),
                intent_kind=primary_intent,
                stat_used="banter",
                risk="medium",
                tone="playful",
            )
        ],
        npc_will_leave=npc_will_leave,
        npc_exit_line="I should go mingle for a bit." if npc_will_leave else None,
    )

def mock_follow_up_menu(intent_kind: str = "joke_back", *, npc_will_leave: bool = False) -> FollowUpMenu:
    """Return a deterministic menu that includes ``intent_kind`` for replay."""
    primary_intent = "joke_back" if intent_kind in EXIT_INTENT_KINDS else intent_kind
    options = [
        FollowUpOption(
            label=_mock_label(primary_intent),
            category=_mock_category(primary_intent),
            intent_kind=primary_intent,
            stat_used="banter",
            risk="medium",
            tone="playful",
        ),
        FollowUpOption(
            label="End on a good note",
            category="exit",
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
    if not 2 <= len(menu.options) <= 5:
        raise ValueError(f"follow-up option count out of bounds: {len(menu.options)}")
    exit_count = sum(option.category == "exit" for option in menu.options)
    if exit_count != 1:
        raise ValueError(f"follow-up menu must contain exactly one exit category option: {menu}")
    for option in menu.options:
        if option.category not in FOLLOW_UP_CATEGORIES:
            raise ValueError(f"unknown follow-up category: {option.category}")
        if option.audience_hint not in {"+", "-", ""}:
            raise ValueError(f"unknown audience_hint: {option.audience_hint}")
        if option.category == "exit" and option.intent_kind not in EXIT_INTENT_KINDS:
            raise ValueError(f"exit option has non-exit intent_kind: {option.intent_kind}")
        if len(option.label.split()) > BESPOKE_LABEL_MAX_WORDS:
            raise ValueError(f"follow-up label too long: {option.label!r}")
        if re.search(r"\d", option.label):
            raise ValueError(f"follow-up label contains digits: {option.label!r}")
        if option.unlock_threshold is not None:
            for key, value in option.unlock_threshold.items():
                if key not in {"affection", "chemistry", "trust", "friendship"}:
                    raise ValueError(f"unknown unlock threshold key: {key}")
                if value < 0 or value > 100:
                    raise ValueError(f"unlock threshold out of range: {option.unlock_threshold}")
    if menu.npc_will_leave:
        if not menu.npc_exit_line:
            raise ValueError("npc_exit_line is required when npc_will_leave is true")
        if len(menu.npc_exit_line.split()) > 40:
            raise ValueError(f"npc_exit_line too long: {menu.npc_exit_line!r}")


def validate_contextual_bespoke(
    bespoke: ContextualBespoke,
    already_present: list[str],
) -> None:
    """Validate the slim Contextual Options output before assembly."""
    if not 1 <= len(bespoke.options) <= 2:
        raise ValueError(f"bespoke option count out of bounds: {len(bespoke.options)}")
    duplicates = set(already_present) & {option.intent_kind for option in bespoke.options}
    if duplicates:
        raise ValueError(f"bespoke duplicated already-present intents: {sorted(duplicates)}")
    for option in bespoke.options:
        if option.intent_kind not in ALLOWED_BESPOKE_INTENTS:
            raise ValueError(f"unknown bespoke intent_kind: {option.intent_kind}")
        if option.category not in FOLLOW_UP_CATEGORIES:
            raise ValueError(f"unknown bespoke category: {option.category}")
        if option.category == "exit":
            raise ValueError("bespoke options must not provide the engine-owned exit")
        if len(option.label.split()) > BESPOKE_LABEL_MAX_WORDS:
            raise ValueError(f"bespoke label too long: {option.label!r}")
        if re.search(r"\d", option.label):
            raise ValueError(f"bespoke label contains digits: {option.label!r}")
    if bespoke.npc_will_leave:
        if not bespoke.npc_exit_line:
            raise ValueError("npc_exit_line is required when npc_will_leave is true")
        if len(bespoke.npc_exit_line.split()) > 40:
            raise ValueError(f"npc_exit_line too long: {bespoke.npc_exit_line!r}")


def with_gossip_options(menu: FollowUpMenu, state: GameState) -> FollowUpMenu:
    """Add deterministic gossip options from active conversation memory offers."""
    conversation = state.active_conversation
    if conversation is None or not conversation.gossip_offers:
        return menu
    existing = {option.intent_kind for option in menu.options}
    if any(intent_kind.startswith("ask_gossip:") for intent_kind in existing):
        return menu
    options = list(menu.options)
    for memory in conversation.gossip_offers:
        intent_kind = f"ask_gossip:{memory.id}"
        if intent_kind in existing:
            continue
        option = FollowUpOption(
            label=f"Ask about {_subject_name(state, memory)}",
            category="gossip",
            intent_kind=intent_kind,
            stat_used="eq",
            risk="medium",
            tone="curious",
        )
        if len(options) < 5:
            options.insert(max(0, len(options) - 1), option)
        else:
            replace_at = next(
                (index for index, existing_option in enumerate(options) if existing_option.category != "exit"),
                0,
            )
            options[replace_at] = option
        break
    return menu.model_copy(update={"options": options})


def _render_context(context: ContextualOptionsContext) -> str:
    return "\n".join(
        [
            f"NPC name: {context.npc_name}",
            f"Archetype voice: {context.npc_archetype}",
            f"Backstory: {context.npc_backstory}",
            f"Current mood: {context.npc_mood}",
            f"Relationship summary: {context.relationship_summary}",
            f"Last NPC line: {context.last_npc_dialogue}",
            f"Last NPC tone: {context.last_npc_tone}",
            f"Recent exchange history: {context.recent_history}",
            "Player stats:",
            f"charm {context.charm}, banter {context.banter}, eq {context.eq}, "
            f"graft {context.graft}, loyalty {context.loyalty}",
            f"Departure probability: {context.departure_probability}",
            f"already_present: {', '.join(context.already_present) or 'none'}",
            f"Gossip-eligible memories: {context.gossip_memories}",
            "Write the bespoke follow-up additions now.",
        ]
    )

def _gossip_memory_context(state: GameState) -> str:
    conversation = state.active_conversation
    if conversation is None or not conversation.gossip_offers:
        return "None."
    return "\n".join(_memory_line(state, memory) for memory in conversation.gossip_offers)

def _memory_line(state: GameState, memory: Memory) -> str:
    return (
        f"- id {memory.id}; subject {_subject_name(state, memory)}; "
        f"weight {memory.emotional_weight}; tags {', '.join(memory.tags)}; "
        f"content {memory.content}"
    )

def _subject_name(state: GameState, memory: Memory) -> str:
    for islander in state.islanders:
        if islander.id == memory.subject_id:
            return islander.name
    return memory.subject_id

def _mock_label(intent_kind: str) -> str:
    labels = {
        "joke_back": "Joke back",
        "go_deeper": "Ask something deeper",
        "honest_vulnerable": "Get vulnerable",
        "escalate_flirt": "Push the flirt",
        "apologize": "Apologize honestly",
        "deflect_with_humor": "Deflect with humor",
        "end_softly": "End on a good note",
        "walk_away": "Walk away",
    }
    return labels.get(intent_kind, intent_kind.replace("_", " ").title())

def _mock_category(intent_kind: str) -> FollowUpCategory:
    if intent_kind in EXIT_INTENT_KINDS:
        return "exit"
    if intent_kind == "escalate_flirt":
        return "flirty"
    if intent_kind in {"joke_back", "deflect_with_humor"}:
        return "banter"
    if intent_kind in {"go_deeper", "honest_vulnerable"}:
        return "deep"
    if intent_kind == "apologize":
        return "supportive"
    return "friendly"
