"""Autopilot helpers for the interactive play command."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from src.game.agents.player_autopilot import (
    PolicyDecision,
    mock_player_autopilot,
    persona_character,
    validate_policy_decision,
)
from src.game.engine.actions import ActionKind, ActionSpec, PlayerAction
from src.game.engine.character_creation import create_character
from src.game.engine.intents import IntentCategory, available_intents_for
from src.game.state.models import GameState, Phase

AutopilotFn = Callable[
    [GameState, Sequence[ActionSpec]],
    PolicyDecision,
]

EXIT_INTENT_IDS = {"end_softly", "walk_away", "change_subject_and_drift"}
AUTOPILOT_MAX_EXCHANGES_PER_CONVERSATION = 3
AUTOPILOT_SOCIAL_PHASES = {Phase.MORNING, Phase.AFTERNOON, Phase.EVENING}


def apply_autopilot_character(state: GameState, persona: str) -> None:
    """Create the player character from the prompt-owned persona targets."""
    choice = persona_character(persona)
    create_character(
        state,
        archetype_id=choice.archetype_id,
        stats=choice.stats,
        rerolled=False,
    )


def expanded_autopilot_actions(state: GameState, actions: Sequence[ActionSpec]) -> list[ActionSpec]:
    """Expand nested conversation intent menus into one autopilot-visible list."""
    expanded: list[ActionSpec] = []
    for spec in actions:
        action = spec.action
        if action.kind is not ActionKind.START_CONVERSATION or action.target_id is None:
            expanded.append(spec)
            continue
        for intent in available_intents_for(state, action.target_id):
            expanded.append(
                ActionSpec(
                    action=PlayerAction(
                        kind=ActionKind.START_CONVERSATION,
                        target_id=action.target_id,
                        intent_id=intent.id,
                    ),
                    label=(
                        f"Talk to {spec.label.removeprefix('Talk to ')} / "
                        f"{_category_label(intent.category)}: {intent.label} ({intent.stat_used})"
                    ),
                )
            )
    return expanded


def decide_with_autopilot(
    state: GameState,
    actions: Sequence[ActionSpec],
    *,
    persona: str,
    recent_history: Sequence[dict[str, object]],
    decider: object | None,
) -> tuple[PlayerAction, PolicyDecision, ActionSpec]:
    """Return the action selected by the configured autopilot."""
    visible_actions = expanded_autopilot_actions(state, actions)
    if not visible_actions:
        raise ValueError("autopilot has no visible actions")
    forced = _mandatory_system_action(state, visible_actions, persona)
    if forced is None:
        forced = _long_conversation_exit(state, visible_actions, persona)
    if forced is None:
        forced = _phase_budget_action(state, visible_actions, persona, recent_history)
    if forced is not None:
        return forced
    visible_actions = _apply_recent_target_cooldown(visible_actions, recent_history)
    if decider is None:
        decision = mock_player_autopilot(
            state,
            visible_actions,
            persona=persona,
            recent_history=recent_history,
        )
    else:
        decision = decider.decide(
            state,
            visible_actions,
            persona=persona,
            recent_history=recent_history,
        )
    validate_policy_decision(decision, len(visible_actions))
    chosen = visible_actions[decision.chosen_action_index]
    return chosen.action, decision, chosen


def _mandatory_system_action(
    state: GameState,
    actions: Sequence[ActionSpec],
    persona: str,
) -> tuple[PlayerAction, PolicyDecision, ActionSpec] | None:
    del state
    priorities = [
        ActionKind.CASA_DECISION,
        ActionKind.HIDEAWAY,
        ActionKind.CHALLENGE_RESPONSE,
    ]
    for kind in priorities:
        for index, spec in enumerate(actions):
            if spec.action.kind is kind:
                decision = PolicyDecision(
                    chosen_action_index=index,
                    rationale=(
                        f"{persona} autopilot resolves the available {kind.value} before optional chats."
                    ),
                    confidence="high",
                )
                return spec.action, decision, spec
    return None


def _phase_budget_action(
    state: GameState,
    actions: Sequence[ActionSpec],
    persona: str,
    recent_history: Sequence[dict[str, object]],
) -> tuple[PlayerAction, PolicyDecision, ActionSpec] | None:
    advance = _advance_spec(actions)
    if state.active_conversation is not None or advance is None:
        return None
    if state.phase not in AUTOPILOT_SOCIAL_PHASES:
        return _forced_decision(
            advance,
            persona,
            f"{persona} autopilot advances through {state.phase.value} after mandatory events resolve.",
        )
    if _conversation_starts_this_phase(state, recent_history) >= 1:
        return _forced_decision(
            advance,
            persona,
            f"{persona} autopilot advances after one focused conversation in this phase.",
        )
    return None


def _advance_spec(actions: Sequence[ActionSpec]) -> tuple[int, ActionSpec] | None:
    for index, spec in enumerate(actions):
        if spec.action.kind is ActionKind.ADVANCE_PHASE:
            return index, spec
    return None


def _forced_decision(
    indexed_spec: tuple[int, ActionSpec],
    persona: str,
    rationale: str,
) -> tuple[PlayerAction, PolicyDecision, ActionSpec]:
    index, spec = indexed_spec
    decision = PolicyDecision(
        chosen_action_index=index,
        rationale=rationale,
        confidence="high",
    )
    return spec.action, decision, spec


def _conversation_starts_this_phase(
    state: GameState,
    recent_history: Sequence[dict[str, object]],
) -> int:
    total = 0
    for record in recent_history:
        if record.get("day") != state.day or record.get("phase") != state.phase.value:
            continue
        action = record.get("action")
        if isinstance(action, dict) and action.get("kind") == ActionKind.START_CONVERSATION.value:
            total += 1
    return total


def _apply_recent_target_cooldown(
    actions: Sequence[ActionSpec],
    recent_history: Sequence[dict[str, object]],
) -> list[ActionSpec]:
    target_id = _recent_exit_target(recent_history)
    if target_id is None:
        return list(actions)
    filtered = [
        spec
        for spec in actions
        if not (
            spec.action.kind is ActionKind.START_CONVERSATION
            and spec.action.target_id == target_id
        )
    ]
    if not filtered:
        return list(actions)
    non_advance = [spec for spec in filtered if spec.action.kind is not ActionKind.ADVANCE_PHASE]
    return non_advance if non_advance else filtered


def _recent_exit_target(recent_history: Sequence[dict[str, object]]) -> str | None:
    for record in reversed(recent_history[-2:]):
        action = record.get("action")
        if not isinstance(action, dict):
            continue
        kind = action.get("kind")
        intent_id = action.get("intent_id")
        if kind != ActionKind.END_CONVERSATION.value and intent_id not in EXIT_INTENT_IDS:
            continue
        target_id = action.get("target_id")
        if isinstance(target_id, str):
            return target_id
        result = record.get("mechanical_result")
        if not isinstance(result, dict):
            continue
        deltas = result.get("relationship_deltas")
        if isinstance(deltas, dict) and deltas:
            first_key = next(iter(deltas))
            if isinstance(first_key, str):
                return first_key
    return None


def _long_conversation_exit(
    state: GameState,
    actions: Sequence[ActionSpec],
    persona: str,
) -> tuple[PlayerAction, PolicyDecision, ActionSpec] | None:
    conversation = state.active_conversation
    if conversation is None or len(conversation.exchanges) < AUTOPILOT_MAX_EXCHANGES_PER_CONVERSATION:
        return None
    for index, spec in enumerate(actions):
        label = spec.label.lower()
        if label.startswith("exit:") or spec.action.kind is ActionKind.END_CONVERSATION:
            decision = PolicyDecision(
                chosen_action_index=index,
                rationale=(
                    f"{persona} autopilot closes the long conversation so the villa day can move forward."
                ),
                confidence="high",
            )
            return spec.action, decision, spec
    return None


def _category_label(category: IntentCategory) -> str:
    return category.value.title()
