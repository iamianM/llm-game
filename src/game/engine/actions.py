"""Available action generation and action validation.

Design sources:
- 05-Interaction-System.md: Hybrid Menu System, Interaction Flow
- 06-Location-System.md: Location-specific actions

Implementation rule:
Action mechanics live in Python. Optional markdown content may provide
narrator-facing flavor, but it must not decide whether an action is valid.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from src.game.engine.casa_amor import casa_decision_options, location_villa, locations_for_villa
from src.game.engine.couples import player_couple
from src.game.engine.hideaway import hideaway_eligible, hideaway_partner_id
from src.game.engine.intents import available_intents_for, get_intent
from src.game.state.models import FollowUpOption, GameState, IslanderState, Location, Phase


class ActionKind(StrEnum):
    """Canonical action vocabulary shared by engine, CLI, browser, and tests."""

    CREATE_CHARACTER = "create_character"
    START_CONVERSATION = "start_conversation"
    RESPOND_WITH = "respond_with"
    END_CONVERSATION = "end_conversation"
    CHALLENGE_RESPONSE = "challenge_response"
    HIDEAWAY = "hideaway"
    CASA_DECISION = "casa_decision"
    MOVE = "move"
    RECOUPLE = "recouple"
    ADVANCE_PHASE = "advance_phase"


class PlayerAction(BaseModel):
    """One player action submitted by CLI, browser, or scenario fixtures."""

    model_config = ConfigDict(extra="forbid")

    kind: ActionKind
    target_id: str | None = None
    intent_id: str | None = None
    option_index: int | None = None
    payload: dict[str, object] | None = None


class ActionSpec(BaseModel):
    """A valid action surfaced to the player."""

    model_config = ConfigDict(extra="forbid")

    action: PlayerAction
    label: str


def available_actions(state: GameState) -> list[ActionSpec]:
    """Return valid actions for the current state."""
    if state.is_terminal:
        return []

    actions: list[ActionSpec] = []
    casa_options = casa_decision_options(state)
    if casa_options:
        return [
            ActionSpec(
                action=PlayerAction(
                    kind=ActionKind.CASA_DECISION,
                    target_id=target_id,
                    intent_id=decision.value,
                ),
                label=label,
            )
            for decision, target_id, label in casa_options
        ]
    if state.pending_challenge is not None and state.pending_challenge.result is None:
        if state.pending_challenge.kind == "snog_marry_pie":
            for islander in state.islanders:
                if not islander.eliminated:
                    actions.append(
                        ActionSpec(
                            action=PlayerAction(
                                kind=ActionKind.CHALLENGE_RESPONSE,
                                target_id=islander.id,
                                payload={"choice": islander.id},
                            ),
                            label=f"Snog Marry Pie: choose {islander.name}",
                        )
                    )
            return actions
    if _needs_initial_coupling(state):
        return [
            ActionSpec(
                action=PlayerAction(kind=ActionKind.RECOUPLE, target_id=islander.id),
                label=f"Initial couple with {islander.name}",
            )
            for islander in _initial_coupling_targets(state)
        ]

    if state.active_conversation is not None:
        interruption = state.active_conversation.pending_interruption
        if interruption is not None:
            interrupter = _find_islander(state, interruption.interrupter_id)
            actions.extend(
                [
                    ActionSpec(
                        action=PlayerAction(
                            kind=ActionKind.RESPOND_WITH,
                            target_id=interrupter.id,
                            intent_id="accept_interruption",
                        ),
                        label=(
                            f"Interruption: Welcome them ({interrupter.name}, "
                            f"{interruption.reason}, {interruption.urgency})"
                        ),
                    ),
                    ActionSpec(
                        action=PlayerAction(
                            kind=ActionKind.RESPOND_WITH,
                            target_id=interrupter.id,
                            intent_id="defer_interruption",
                        ),
                        label="Interruption: Politely defer",
                    ),
                    ActionSpec(
                        action=PlayerAction(
                            kind=ActionKind.RESPOND_WITH,
                            target_id=interrupter.id,
                            intent_id="ignore_interruption",
                        ),
                        label="Interruption: Ignore them",
                    ),
                ]
            )
        menu = state.active_conversation.pending_options
        if menu is not None and not menu.npc_will_leave:
            target = _find_islander(state, state.active_conversation.target_id)
            for index, option in _unlocked_follow_up_options(menu.options, target):
                actions.append(
                    ActionSpec(
                        action=PlayerAction(
                            kind=ActionKind.RESPOND_WITH,
                            target_id=state.active_conversation.target_id,
                            intent_id=option.intent_kind,
                            option_index=index,
                        ),
                        label=(
                            f"{option.category.title()}: {option.label} "
                            f"({option.stat_used or 'exit'}, {option.risk})"
                        ),
                    )
                )
        actions.append(
            ActionSpec(action=PlayerAction(kind=ActionKind.END_CONVERSATION), label="Walk away (curt)")
        )
        return actions

    for islander in state.islanders:
        if islander.location_id != state.location_id or islander.eliminated:
            continue
        if location_villa(islander.location_id) is not state.villa:
            continue
        actions.append(
            ActionSpec(
                action=PlayerAction(kind=ActionKind.START_CONVERSATION, target_id=islander.id),
                label=f"Talk to {islander.name}",
            )
        )
    if hideaway_eligible(state):
        partner_id = hideaway_partner_id(state)
        partner = _find_islander(state, partner_id) if partner_id is not None else None
        label = "Spend the night in the Hideaway"
        if partner is not None:
            label = f"Spend the night in the Hideaway with {partner.name}"
        actions.append(ActionSpec(action=PlayerAction(kind=ActionKind.HIDEAWAY), label=label))
    if state.phase in {Phase.MORNING, Phase.AFTERNOON}:
        for location in locations_for_villa(state.villa):
            if location != state.location_id and location is not Location.HIDEAWAY:
                actions.append(
                    ActionSpec(
                        action=PlayerAction(kind=ActionKind.MOVE, target_id=location.value),
                        label=f"Move to {location.value}",
                    )
                )
    actions.append(
        ActionSpec(
            action=PlayerAction(kind=ActionKind.ADVANCE_PHASE),
            label="Advance phase",
        )
    )
    return actions


def validate_action(state: GameState, action: PlayerAction) -> None:
    """Raise if ``action`` is not valid for ``state``."""
    if action.kind is ActionKind.CREATE_CHARACTER:
        if state.character_creation is not None:
            raise ValueError("character has already been created")
        if state.turn_index != 0:
            raise ValueError("character creation is only valid before the run starts")
        return
    if action.kind is ActionKind.START_CONVERSATION:
        if state.active_conversation is not None:
            raise ValueError("cannot start a conversation while one is active")
        if action.target_id is None or action.intent_id is None:
            raise ValueError("START_CONVERSATION requires target_id and intent_id")
        try:
            target = _find_islander(state, action.target_id)
        except ValueError as exc:
            raise ValueError(f"target is not visible in the current villa: {action.model_dump()}") from exc
        if target.location_id != state.location_id or location_villa(target.location_id) is not state.villa:
            raise ValueError(f"target is not visible in the current villa: {action.model_dump()}")
        valid_intents = {intent.id for intent in available_intents_for(state, action.target_id)}
        if action.intent_id not in valid_intents:
            get_intent(action.intent_id)
            raise ValueError(f"intent is locked or unavailable: {action.model_dump()}")
        return
    if action.kind is ActionKind.RESPOND_WITH:
        conversation = state.active_conversation
        if conversation is None:
            raise ValueError("cannot respond without an active conversation")
        if (
            conversation.pending_interruption is not None
            and action.intent_id
            in {"accept_interruption", "defer_interruption", "ignore_interruption"}
        ):
            return
        menu = conversation.pending_options
        if menu is None:
            raise ValueError("active conversation has no pending options")
        target = _find_islander(state, conversation.target_id)
        unlocked = dict(_unlocked_follow_up_options(menu.options, target))
        if action.option_index is not None:
            if action.option_index not in unlocked:
                raise ValueError(f"invalid follow-up option index: {action.model_dump()}")
            return
        if action.intent_id is not None and any(
            option.intent_kind == action.intent_id for option in unlocked.values()
        ):
            return
        raise ValueError(f"RESPOND_WITH requires valid option_index or intent_id: {action.model_dump()}")
    if action.kind is ActionKind.END_CONVERSATION:
        if state.active_conversation is None:
            raise ValueError("cannot end conversation when none is active")
        return
    if action.kind is ActionKind.CHALLENGE_RESPONSE:
        if state.pending_challenge is None or state.pending_challenge.result is not None:
            raise ValueError("no challenge is waiting for a response")
        if action.target_id is None:
            raise ValueError("CHALLENGE_RESPONSE requires target_id")
        _find_islander(state, action.target_id)
        return
    if action.kind is ActionKind.HIDEAWAY:
        if player_couple(state) is None:
            raise ValueError("Hideaway requires a player couple")
        if not hideaway_eligible(state):
            raise ValueError("Hideaway is not available")
        return
    if action.kind is ActionKind.CASA_DECISION:
        valid = [spec.action for spec in available_actions(state)]
        if action not in valid:
            raise ValueError(f"invalid Casa Amor decision: {action.model_dump()}")
        return
    valid = [spec.action for spec in available_actions(state)]
    if action not in valid:
        raise ValueError(f"invalid action for current state: {action.model_dump()}")


def _unlocked_follow_up_options(
    options: list[FollowUpOption],
    target: IslanderState,
) -> list[tuple[int, FollowUpOption]]:
    return [
        (index, option)
        for index, option in enumerate(options)
        if _meets_unlock_threshold(option, target)
    ]


def _meets_unlock_threshold(option: FollowUpOption, target: IslanderState) -> bool:
    if option.unlock_threshold is None:
        return True
    relationship = target.relationship
    for key, required in option.unlock_threshold.items():
        value = getattr(relationship, key)
        if not isinstance(value, int) or value < required:
            return False
    return True


def _needs_initial_coupling(state: GameState) -> bool:
    return (
        state.day == 1
        and state.phase is Phase.MORNING
        and not state.couples
        and state.character_creation is not None
    )


def _initial_coupling_targets(state: GameState) -> list[IslanderState]:
    targets = [
        islander
        for islander in state.islanders
        if not islander.eliminated
        and islander.gender != state.player.gender
        and location_villa(islander.location_id) is state.villa
    ]
    return sorted(targets, key=lambda islander: (islander.name, islander.id))


def _find_islander(state: GameState, target_id: str) -> IslanderState:
    for islander in state.islanders:
        if islander.id == target_id:
            return islander
    raise ValueError(f"unknown islander: {target_id}")
