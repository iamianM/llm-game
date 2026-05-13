"""Player Autopilot agent for self-play validation."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from src.game.agents.islander_voice import load_dotenv_local
from src.game.engine.actions import ActionKind, ActionSpec
from src.game.engine.compatibility import revealed_preferences
from src.game.engine.couples import couple_strength, player_couple
from src.game.state.casa import CasaDecision
from src.game.state.models import GameState, PlayerStats

PLAYER_AUTOPILOT_MODEL = "gpt-4.1-mini"
AUTOPILOT_PERSONAS = {"loyal", "player", "chaotic"}


class PolicyDecision(BaseModel):
    """One committed autopilot choice."""

    model_config = ConfigDict(extra="forbid")

    chosen_action_index: int = Field(ge=0)
    rationale: str
    confidence: Literal["high", "medium", "low"]


class AutopilotCharacter(BaseModel):
    """Deterministic character creation choice for an autopilot persona."""

    model_config = ConfigDict(extra="forbid")

    archetype_id: str
    stats: PlayerStats


class OpenAIPlayerAutopilot:
    """Structured player autopilot backed by OpenAI Responses."""

    def __init__(self, *, model: str = PLAYER_AUTOPILOT_MODEL) -> None:
        load_dotenv_local()
        self._client = OpenAI()
        self._model = model

    def decide(
        self,
        state: GameState,
        actions: Sequence[ActionSpec],
        *,
        persona: str,
        recent_history: Sequence[dict[str, object]],
    ) -> PolicyDecision:
        """Pick one action from the visible action list."""
        _validate_persona(persona)
        if not actions:
            raise ValueError("autopilot requires at least one available action")
        forced = forced_persona_decision(actions, persona)
        if forced is not None:
            return forced
        rendered = _render_context(state, actions, persona=persona, recent_history=recent_history)
        last_error: ValueError | None = None
        for attempt in range(3):
            context = rendered
            if last_error is not None:
                context = (
                    f"{rendered}\n\nPrevious PolicyDecision failed validation: {last_error}. "
                    "Return a corrected PolicyDecision with an in-range action index."
                )
            decision = self._generate_decision(context)
            try:
                validate_policy_decision(decision, len(actions))
                validate_persona_decision(decision, state, actions, persona)
                return decision
            except ValueError as exc:
                last_error = exc
                if attempt == 2:
                    raise
        raise AssertionError("unreachable autopilot retry state")

    def _generate_decision(self, rendered_context: str) -> PolicyDecision:
        response = self._client.responses.parse(
            model=self._model,
            instructions=Path("src/game/agents/prompts/player_autopilot.md").read_text(
                encoding="utf-8"
            ),
            input=rendered_context,
            text_format=PolicyDecision,
            max_output_tokens=500,
        )
        decision = response.output_parsed
        if decision is None:
            raise ValueError("Player Autopilot returned no parsed PolicyDecision")
        return decision


def persona_character(persona: str) -> AutopilotCharacter:
    """Return the prompt-owned character creation choice for a persona."""
    _validate_persona(persona)
    if persona == "loyal":
        return AutopilotCharacter(
            archetype_id="loyal_friend",
            stats=PlayerStats(charm=5, banter=5, eq=8, graft=4, loyalty=8),
        )
    if persona == "chaotic":
        return AutopilotCharacter(
            archetype_id="class_clown",
            stats=PlayerStats(charm=6, banter=8, eq=4, graft=8, loyalty=3),
        )
    return AutopilotCharacter(
        archetype_id="heartthrob",
        stats=PlayerStats(charm=8, banter=7, eq=5, graft=6, loyalty=4),
    )


def mock_player_autopilot(
    state: GameState,
    actions: Sequence[ActionSpec],
    *,
    persona: str = "loyal",
    recent_history: Sequence[dict[str, object]] = (),
) -> PolicyDecision:
    """Deterministic non-LLM autopilot used by tests."""
    del recent_history
    _validate_persona(persona)
    if not actions:
        raise ValueError("mock autopilot requires actions")
    index = _preferred_index(state, actions, persona)
    return PolicyDecision(
        chosen_action_index=index,
        rationale=f"{persona} autopilot chose {actions[index].label} for the current situation.",
        confidence="high",
    )


def validate_policy_decision(decision: PolicyDecision, action_count: int) -> None:
    """Fail loud if a PolicyDecision cannot be applied."""
    if not 0 <= decision.chosen_action_index < action_count:
        raise ValueError(
            f"chosen_action_index out of range: {decision.chosen_action_index} for {action_count} actions"
        )
    words = decision.rationale.split()
    if not 3 <= len(words) <= 60:
        raise ValueError("autopilot rationale must be a short concrete sentence")


def validate_persona_decision(
    decision: PolicyDecision,
    state: GameState,
    actions: Sequence[ActionSpec],
    persona: str,
) -> None:
    """Enforce prompt-owned persona rules for headline commitment decisions."""
    del state
    action = actions[decision.chosen_action_index].action
    casa_actions = [spec.action for spec in actions if spec.action.kind is ActionKind.CASA_DECISION]
    if casa_actions == []:
        return
    if persona == "loyal" and action.intent_id != CasaDecision.RETURN_WITH_ORIGINAL.value:
        raise ValueError("loyal persona must return with the original partner at Casa Amor")
    if persona == "chaotic" and action.intent_id != CasaDecision.RETURN_WITH_NEW.value:
        raise ValueError("chaotic persona must return with a Casa Amor islander when available")


def forced_persona_decision(
    actions: Sequence[ActionSpec],
    persona: str,
) -> PolicyDecision | None:
    """Return deterministic choices for prompt-defined headline persona rules."""
    _validate_persona(persona)
    casa_indices = [
        (index, spec.action)
        for index, spec in enumerate(actions)
        if spec.action.kind is ActionKind.CASA_DECISION
    ]
    if casa_indices == []:
        return None
    if persona == "loyal":
        for index, action in casa_indices:
            if action.intent_id == CasaDecision.RETURN_WITH_ORIGINAL.value:
                return PolicyDecision(
                    chosen_action_index=index,
                    rationale="Returning to the original partner preserves the loyal persona's commitment.",
                    confidence="high",
                )
    if persona == "chaotic":
        for index, action in casa_indices:
            if action.intent_id == CasaDecision.RETURN_WITH_NEW.value:
                return PolicyDecision(
                    chosen_action_index=index,
                    rationale="Returning with a Casa islander creates the instability the chaotic persona wants.",
                    confidence="high",
                )
    return None


def _preferred_index(state: GameState, actions: Sequence[ActionSpec], persona: str) -> int:
    labels = [action.label.lower() for action in actions]
    if any("return with" in label or "return single" in label for label in labels):
        if persona == "loyal":
            return _first_label(labels, "original", default=0)
        if persona == "chaotic":
            return _first_label(labels, "return with", skip="original", default=0)
    if persona == "chaotic":
        for needle in ("escalate", "flirt", "gossip", "pull", "ignore"):
            found = _first_label(labels, needle, default=-1)
            if found >= 0:
                return found
    if state.hideaway.partner_id is not None:
        found = _first_label(labels, "hideaway", default=-1)
        if found >= 0:
            return found
    advance = _first_label(labels, "advance phase", default=-1)
    if advance >= 0 and state.turn_index >= 2:
        return advance
    if persona == "loyal":
        for needle in ("chloe", "deeper", "honest", "end on a good note", "advance phase"):
            found = _first_label(labels, needle, default=-1)
            if found >= 0:
                return found
    return 0


def _first_label(labels: Sequence[str], needle: str, *, skip: str = "", default: int) -> int:
    for index, label in enumerate(labels):
        if needle in label and (not skip or skip not in label):
            return index
    return default


def _validate_persona(persona: str) -> None:
    if persona not in AUTOPILOT_PERSONAS:
        raise ValueError(f"unknown autopilot persona: {persona}")


def _render_context(
    state: GameState,
    actions: Sequence[ActionSpec],
    *,
    persona: str,
    recent_history: Sequence[dict[str, object]],
) -> str:
    stats = state.player.stats
    action_lines = "\n".join(
        f"{index}: {spec.label} -> {spec.action.model_dump(mode='json', exclude_none=True)}"
        for index, spec in enumerate(actions)
    )
    islanders = "\n".join(
        (
            f"- {islander.id}: {islander.name}, location {islander.location_id.value}, "
            f"mood {islander.mood.value}, affection {islander.relationship.affection}, "
            f"chemistry {islander.relationship.chemistry}, trust {islander.relationship.trust}, "
            f"friendship {islander.relationship.friendship}, revealed type {revealed_preferences(islander)}"
        )
        for islander in state.islanders
        if not islander.eliminated and islander.location_id == state.location_id
    )
    couple = player_couple(state)
    couple_text = "none" if couple is None else f"{couple.model_dump(mode='json')}, strength {couple_strength(state, couple)}"
    history = "\n".join(str(item) for item in recent_history[-3:]) or "none"
    active = "none" if state.active_conversation is None else state.active_conversation.model_dump_json()
    audience = "none" if state.audience_snapshots == [] else state.audience_snapshots[-1].model_dump_json()
    return "\n".join(
        [
            f"Persona: {persona}",
            f"Day: {state.day}",
            f"Phase: {state.phase.value}",
            f"Turn: {state.turn_index}",
            f"Player archetype: {state.player.archetype_id}",
            (
                f"Stats: charm {stats.charm}, banter {stats.banter}, eq {stats.eq}, "
                f"graft {stats.graft}, loyalty {stats.loyalty}"
            ),
            f"Public perception: {state.player.public_perception}",
            f"Current villa: {state.villa.value}",
            f"Location: {state.location_id.value}",
            f"Couple: {couple_text}",
            f"Active conversation: {active}",
            f"Audience snapshot: {audience}",
            f"Recent history: {history}",
            "Visible islanders:",
            islanders or "none",
            "Available actions:",
            action_lines,
            "Choose one action index now.",
        ]
    )
