"""Contextual follow-up menu agent.

Design sources:
- docs/design/03-LLM-Architecture.md: Dialogue AI
- docs/design/11-Conversation-Flow.md: Contextual Follow-up Generation

Implementation rule:
The agent proposes follow-up choices and departure flavor only. Deterministic
engine code validates the menu and resolves mechanics.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import cached_property
from pathlib import Path
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from src.game.agents.contextual_gossip import with_gossip_options as with_gossip_options
from src.game.agents.heartbreaker_voice import Exchange, load_dotenv_local
from src.game.agents.runtime import (
    UTILITY_PROFILE,
    AgentGenerationError,
    AgentValidationError,
    begin_agent_attempt,
    build_game_client,
    end_agent_attempt,
    mark_agent_trace_generation_error,
    mark_agent_trace_validation_error,
    reasoning_request_kwargs,
    record_agent_trace,
    start_agent_call,
)
from src.game.engine.rules import MechanicalResult
from src.game.state.models import FollowUpMenu, FollowUpOption, GameState, Memory

CONTEXTUAL_OPTIONS_MODEL = UTILITY_PROFILE.model
CONTEXTUAL_OPTIONS_REASONING_EFFORT = UTILITY_PROFILE.reasoning_effort
CONTEXTUAL_OPTIONS_PROMPT = "src/game/agents/prompts/contextual_options.md"
_CONTEXTUAL_OPTIONS_PROMPT_FILE = Path(__file__).parent / "prompts" / "contextual_options.md"
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
    spark: int
    loyalty: int
    departure_probability: int
    gossip_memories: str
    explored_threads: str = "None yet — this is fresh ground."
    already_present: list[str] = Field(default_factory=list)


class ContextualBespoke(BaseModel):
    """Moment-specific additions to a partially-built follow-up wheel.

    The prompt instructs the model to produce one or two bespoke options;
    the schema only enforces non-emptiness so assembly always has something
    to merge.
    """

    model_config = ConfigDict(extra="forbid")

    options: list[FollowUpOption] = Field(min_length=1)
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
        return build_game_client()

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
            attempt_number = attempt + 1
            retry_context = rendered
            if last_error is not None:
                retry_context = (
                    f"{rendered}\n\n"
                    "The previous ContextualBespoke failed validation. "
                    f"Validation error: {last_error}. "
                    "Return a corrected ContextualBespoke with one or two specific options "
                    "that do not duplicate already_present."
                )
            attempt_token = begin_agent_attempt(attempt_number)
            try:
                try:
                    bespoke = self._generate_bespoke(retry_context)
                except Exception as exc:
                    mark_agent_trace_generation_error("contextual_options", attempt_number, exc)
                    last_error = ValueError(str(exc))
                    if attempt == 2:
                        raise AgentGenerationError(str(exc)) from exc
                    continue
            finally:
                end_agent_attempt(attempt_token)
            try:
                validate_contextual_bespoke(bespoke, context.already_present)
                return bespoke
            except ValueError as exc:
                mark_agent_trace_validation_error("contextual_options", attempt_number, exc)
                last_error = exc
                if attempt == 2:
                    raise AgentValidationError(str(exc)) from exc
        raise AssertionError("unreachable contextual options retry state")

    def _generate_bespoke(self, rendered_context: str) -> ContextualBespoke:
        """Request one parsed bespoke option set from the model."""
        instructions = _CONTEXTUAL_OPTIONS_PROMPT_FILE.read_text(encoding="utf-8")
        started_at = start_agent_call()
        response = self._client.responses.parse(
            model=self._model,
            instructions=instructions,
            input=rendered_context,
            text_format=ContextualBespoke,
            **reasoning_request_kwargs(effort=CONTEXTUAL_OPTIONS_REASONING_EFFORT),
        )
        bespoke = response.output_parsed
        record_agent_trace(
            agent_name="contextual_options",
            model=self._model,
            prompt_path=CONTEXTUAL_OPTIONS_PROMPT,
            response=response,
            output=bespoke,
            reasoning_effort=CONTEXTUAL_OPTIONS_REASONING_EFFORT,
            prompt_text=instructions,
            input_payload=rendered_context,
            started_at=started_at,
        )
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
    target = next((heartbreaker for heartbreaker in state.heartbreakers if heartbreaker.id == target_id), None)
    if target is None:
        raise ValueError(f"contextual options target not found: {target_id}")
    stats = state.player.stats
    recent_history = "No prior exchanges."
    if state.active_conversation is not None and state.active_conversation.exchanges:
        recent_history = "\n".join(
            f"- player tried {record.intent_id}; NPC tone {record.npc_tone}; success {record.success}"
            for record in state.active_conversation.exchanges
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
        spark=stats.spark,
        loyalty=stats.loyalty,
        departure_probability=departure_probability,
        gossip_memories=_gossip_memory_context(state),
        explored_threads=_explored_threads(state, target.id),
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
    """Fail loud if a follow-up menu violates the engine contract.

    Only enforces the structural contract: exit is engine-owned (exactly one),
    enum values, and unlock-threshold value ranges. Label length, option
    count, and digit-vs-spelled-number preferences are conveyed via the
    prompt, not enforced here.
    """
    if not menu.options:
        raise ValueError("follow-up menu has no options")
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
        if option.unlock_threshold is not None:
            for key, value in option.unlock_threshold.items():
                if key not in {"affection", "chemistry", "trust", "friendship"}:
                    raise ValueError(f"unknown unlock threshold key: {key}")
                if value < 0 or value > 100:
                    raise ValueError(f"unlock threshold out of range: {option.unlock_threshold}")
    if menu.npc_will_leave and not menu.npc_exit_line:
        raise ValueError("npc_exit_line is required when npc_will_leave is true")


def validate_contextual_bespoke(
    bespoke: ContextualBespoke,
    already_present: list[str],
) -> None:
    """Validate the slim Contextual Options output before assembly.

    Only enforces the structural contract: bespoke options must come from the
    allowed intent set, must not provide the engine-owned exit, and must not
    duplicate intents already present in the default menu. Label length and
    digit-vs-spelled-number preferences are conveyed via the prompt.
    """
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
    if bespoke.npc_will_leave and not bespoke.npc_exit_line:
        raise ValueError("npc_exit_line is required when npc_will_leave is true")


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
            f"spark {context.spark}, loyalty {context.loyalty}",
            f"Departure probability: {context.departure_probability}",
            f"already_present: {', '.join(context.already_present) or 'none'}",
            f"Gossip-eligible memories: {context.gossip_memories}",
            f"Already explored with this Heartbreaker (past chats — do not re-open):\n{context.explored_threads}",
            "Write the bespoke follow-up additions now.",
        ]
    )

def _explored_threads(state: GameState, target_id: str) -> str:
    """Summarize topics the player has already dug into with this NPC.

    Sourced from the player's own memories about this NPC, which persist
    across conversations (unlike ``active_conversation`` history, which resets
    every time the player re-approaches). This lets the agent advance to fresh
    ground instead of re-opening the same single most-salient backstory beat
    on the first turn of every new chat. Returns the most recent few in
    chronological order (oldest first, newest last).
    """
    threads = [
        memory.content.strip()
        for memory in state.player.memories
        if memory.subject_id == target_id and memory.content and memory.content.strip()
    ]
    if not threads:
        return "None yet — this is fresh ground."
    return "\n".join(f"- {content}" for content in threads[-5:])


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
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == memory.subject_id:
            return heartbreaker.name
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
