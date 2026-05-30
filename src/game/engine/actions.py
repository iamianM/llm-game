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

from src.game.content.ambient import ambient_options_for, get_ambient_option
from src.game.engine.action_availability import (
    initial_coupling_targets,
    intro_actions,
    needs_initial_coupling,
    pending_recouple_proposal_actions,
    player_proposal_eligible,
)
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
    JOIN_GATHER = "join_gather"
    AMBIENT = "ambient"
    INTRODUCE_TO = "introduce_to"
    MOVE = "move"
    RECOUPLE = "recouple"
    PROPOSE_RECOUPLE = "propose_recouple"
    NPC_PROPOSAL_RESPONSE = "npc_proposal_response"


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
    if state.pending_gather is not None:
        # Recoupling ceremonies: surface a partner-pick menu so the player
        # makes the central Day-3/Day-5 decision instead of having the engine
        # auto-pair them with their current partner. Picking RECOUPLE in this
        # context resolves the ceremony with the chosen partner; "Stay with"
        # is the explicit no-op pick. If the player is eliminated or has no
        # eligible opposite-sex islanders left, fall through to JOIN_GATHER.
        if (
            state.pending_gather.kind == "ceremony"
            and state.pending_gather.event_id.startswith("recoupling")
            and not state.player.eliminated
        ):
            picks = _recoupling_pick_actions(state)
            if picks:
                return picks
        return [
            ActionSpec(
                action=PlayerAction(kind=ActionKind.JOIN_GATHER),
                label=f"Join gather at the {state.pending_gather.gather_location.value}",
            )
        ]
    if state.pending_recouple_proposal is not None:
        return pending_recouple_proposal_actions(state)
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
        from src.game.engine.challenges import ROUND_BASED_MINIGAMES
        if state.pending_challenge.kind in ROUND_BASED_MINIGAMES:
            current_index = state.pending_challenge.current_round_index
            if current_index < len(state.pending_challenge.rounds):
                current = state.pending_challenge.rounds[current_index]
                # Round-based minigames resolve purely via payload.choice_id;
                # target_id is advisory metadata. Only set it when the choice
                # itself names an islander (e.g. snog_marry_pie picks a person).
                # For answer-based quizzes fact_value is an answer string, so
                # leave target_id unset rather than tagging every option with the
                # player's partner id, which misleads the LLM agents/decider and
                # pollutes telemetry.
                islander_ids = {islander.id for islander in state.islanders}
                for choice in current.choices:
                    choice_target = choice.fact_value if choice.fact_value in islander_ids else None
                    actions.append(
                        ActionSpec(
                            action=PlayerAction(
                                kind=ActionKind.CHALLENGE_RESPONSE,
                                target_id=choice_target,
                                payload={"choice_id": choice.id, "round_index": current_index},
                            ),
                            label=f"Quiz r{current.index + 1}/{len(state.pending_challenge.rounds)}: {choice.label}",
                        )
                    )
                return actions

    if needs_initial_coupling(state):
        return [
            ActionSpec(
                action=PlayerAction(kind=ActionKind.RECOUPLE, target_id=islander.id),
                label=f"Initial couple with {islander.name}",
            )
            for islander in initial_coupling_targets(state)
        ]
    if state.phase is Phase.INTROS:
        return intro_actions(state)

    if state.active_conversation is not None:
        interruption = state.active_conversation.pending_interruption
        if interruption is not None:
            interrupter = _find_islander(state, interruption.interrupter_id)
            iname = interrupter.name
            accept_label = {
                "jealous": f"Turn and hear {iname} out",
                "has_gossip": f"Turn to {iname} for the gossip",
                "drawn_to_topic": f"Bring {iname} into the chat",
                "needs_to_talk": f"Give {iname} your attention",
            }.get(interruption.reason, f"Turn and welcome {iname}")
            actions.extend(
                [
                    ActionSpec(
                        action=PlayerAction(
                            kind=ActionKind.RESPOND_WITH,
                            target_id=interrupter.id,
                            intent_id="accept_interruption",
                        ),
                        label=accept_label,
                    ),
                    ActionSpec(
                        action=PlayerAction(
                            kind=ActionKind.RESPOND_WITH,
                            target_id=interrupter.id,
                            intent_id="defer_interruption",
                        ),
                        label=f"Ask {iname} for a minute",
                    ),
                    ActionSpec(
                        action=PlayerAction(
                            kind=ActionKind.RESPOND_WITH,
                            target_id=interrupter.id,
                            intent_id="ignore_interruption",
                        ),
                        label=f"Ignore {iname} and keep talking",
                    ),
                ]
            )
        menu = state.active_conversation.pending_options
        if player_proposal_eligible(state, state.active_conversation.target_id):
            target = _find_islander(state, state.active_conversation.target_id)
            actions.append(
                ActionSpec(
                    action=PlayerAction(kind=ActionKind.PROPOSE_RECOUPLE, target_id=target.id),
                    label=f"Ask {target.name} to recouple with you",
                )
            )
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

    if state.pending_npc_approach is not None:
        approach = state.pending_npc_approach
        approacher = _find_islander(state, approach.npc_id)
        name = approacher.name
        engage_label = {
            "wants_to_chat": f"Welcome {name} over for a chat",
            "has_gossip": f"Lean in — let {name} spill the gossip",
            "flirty": f"Flirt back with {name}",
            "curious": f"See what {name} wants",
        }.get(approach.reason, f"Welcome {name} over")
        return [
            ActionSpec(
                action=PlayerAction(
                    kind=ActionKind.RESPOND_WITH,
                    target_id=approacher.id,
                    intent_id="engage_approach",
                ),
                label=engage_label,
            ),
            ActionSpec(
                action=PlayerAction(
                    kind=ActionKind.RESPOND_WITH,
                    target_id=approacher.id,
                    intent_id="wave_off_politely",
                ),
                label=f"Wave {name} off gently",
            ),
            ActionSpec(
                action=PlayerAction(
                    kind=ActionKind.RESPOND_WITH,
                    target_id=approacher.id,
                    intent_id="wave_off_firmly",
                ),
                label=f"Brush {name} off",
            ),
            ActionSpec(
                action=PlayerAction(
                    kind=ActionKind.RESPOND_WITH,
                    target_id=approacher.id,
                    intent_id="ignore_approach",
                ),
                label=f"Pretend not to notice {name}",
            ),
        ]

    for islander in state.islanders:
        if islander.location_id != state.location_id or islander.eliminated:
            continue
        if location_villa(islander.location_id) is not state.villa:
            continue
        # Surface one categorized opener per unlocked intent so the free-time
        # CharacterMenu tree (Friendly / Flirty / Deep / Banter) populates from
        # real intents instead of a single generic "Talk to X" that buckets
        # into Banter and leaves the other categories falsely locked. The web
        # groups these by category and drills to a sub-intent; the bottom fan /
        # LLM decider see the self-contained "Talk to X — <opener>" label.
        for intent in available_intents_for(state, islander.id):
            actions.append(
                ActionSpec(
                    action=PlayerAction(
                        kind=ActionKind.START_CONVERSATION,
                        target_id=islander.id,
                        intent_id=intent.id,
                    ),
                    label=f"Talk to {islander.name} — {intent.label}",
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
    if state.phase in {Phase.MORNING, Phase.AFTERNOON, Phase.EVENING}:
        actions.append(
            ActionSpec(
                action=PlayerAction(kind=ActionKind.AMBIENT, target_id="ambient_wait"),
                label=_ambient_wait_label(state),
            )
        )
        for ambient_option in ambient_options_for(state.location_id):
            actions.append(
                ActionSpec(
                    action=PlayerAction(kind=ActionKind.AMBIENT, target_id=ambient_option.id),
                    label=ambient_option.label,
                )
            )
    return actions


def _ambient_wait_label(state: GameState) -> str:
    """Signpost where letting the clock run actually leads.

    On the evenings that gate a mandatory ceremony, spending the rest of the
    phase doesn't just "let the villa move on" — it convenes the night's big
    beat: the Final Vote on the last day, a Pairing Ceremony on Days 3 and 5.
    A generic label buries the game's most important moments behind an
    innocuous skip, so a player (or the LLM decider) can chat past the ending
    forever without realising this is the way to it. Name the destination on
    those nights; stay generic otherwise. Mirrors the scheduling conditions in
    ``advance_phase_with_events``.
    """
    if state.phase is Phase.EVENING:
        casa_active = (
            state.casa_amor_state is not None and not state.casa_amor_state.returned
        )
        if state.day >= 6:
            return "It's time — gather everyone at the firepit for the Final Vote"
        if state.day in {3, 5} and not (state.day == 5 and casa_active):
            return "It's time — gather everyone at the firepit for the Pairing Ceremony"
    return "Let the villa move on"


def _recoupling_pick_actions(state: GameState) -> list[ActionSpec]:
    """Return RECOUPLE picks for a pending recoupling gather.

    Surfaces one option per eligible opposite-sex islander, plus an explicit
    "Stay with <partner>" option when the player is currently coupled. The
    target list mirrors `recoupling()`'s opposite-sex constraint.
    """
    eligible = [
        islander
        for islander in state.islanders
        if not islander.eliminated and islander.gender != state.player.gender
    ]
    if not eligible:
        return []
    eligible.sort(key=lambda i: i.name)
    current_partner_id: str | None = None
    for couple in state.couples:
        if state.player.id in {couple.partner_a_id, couple.partner_b_id}:
            current_partner_id = (
                couple.partner_b_id if couple.partner_a_id == state.player.id else couple.partner_a_id
            )
            break
    picks: list[ActionSpec] = []
    for islander in eligible:
        is_current = islander.id == current_partner_id
        label = (
            f"Stay with {islander.name}"
            if is_current
            else f"Couple with {islander.name}"
        )
        picks.append(
            ActionSpec(
                action=PlayerAction(kind=ActionKind.RECOUPLE, target_id=islander.id),
                label=label,
            )
        )
    return picks


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
        if action.intent_id in {
            "engage_approach",
            "wave_off_politely",
            "wave_off_firmly",
            "ignore_approach",
        }:
            if state.pending_npc_approach is None:
                raise ValueError("no NPC approach is waiting")
            if (
                action.target_id is not None
                and action.target_id != state.pending_npc_approach.npc_id
            ):
                raise ValueError("approach response target must be the approacher")
            return
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
    if action.kind is ActionKind.PROPOSE_RECOUPLE:
        if state.active_conversation is None:
            raise ValueError("cannot propose recoupling outside an active conversation")
        if action.target_id is None:
            raise ValueError("PROPOSE_RECOUPLE requires target_id")
        if action.target_id != state.active_conversation.target_id:
            raise ValueError("recoupling proposal target must be the active conversation target")
        if not player_proposal_eligible(state, action.target_id):
            raise ValueError(f"recoupling proposal is not available: {action.model_dump()}")
        return
    if action.kind is ActionKind.NPC_PROPOSAL_RESPONSE:
        if state.pending_recouple_proposal is None:
            raise ValueError("no NPC recoupling proposal is waiting")
        if action.target_id != state.pending_recouple_proposal.proposer_id:
            raise ValueError("NPC proposal response target must be the proposer")
        if action.intent_id not in {"accept", "decline_politely", "decline_harshly"}:
            raise ValueError(f"invalid NPC proposal response: {action.model_dump()}")
        return
    if action.kind is ActionKind.CHALLENGE_RESPONSE:
        if state.pending_challenge is None or state.pending_challenge.result is not None:
            raise ValueError("no challenge is waiting for a response")
        from src.game.engine.challenges import ROUND_BASED_MINIGAMES
        if state.pending_challenge.kind in ROUND_BASED_MINIGAMES:
            if action.payload is None or "choice_id" not in action.payload:
                raise ValueError("round-based CHALLENGE_RESPONSE requires payload.choice_id")
            cur_index = state.pending_challenge.current_round_index
            if cur_index >= len(state.pending_challenge.rounds):
                raise ValueError("no active minigame round to respond to")
            current = state.pending_challenge.rounds[cur_index]
            choice_id = action.payload["choice_id"]
            if not any(c.id == choice_id for c in current.choices):
                raise ValueError(f"invalid choice_id for current round: {action.model_dump()}")
            return
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
    if action.kind is ActionKind.JOIN_GATHER:
        if state.pending_gather is None:
            raise ValueError("no gather is waiting to resolve")
        return
    if action.kind is ActionKind.AMBIENT:
        if action.target_id is None:
            raise ValueError("AMBIENT requires target_id")
        option = get_ambient_option(action.target_id)
        if option.id != "ambient_wait" and option.location is not state.location_id:
            raise ValueError(f"ambient option is unavailable at current location: {action.model_dump()}")
        if option.id != "ambient_wait" and state.phase not in {Phase.MORNING, Phase.AFTERNOON, Phase.EVENING}:
            raise ValueError("ambient actions are only valid during social phases")
        return
    if action.kind is ActionKind.INTRODUCE_TO:
        if state.phase is not Phase.INTROS:
            raise ValueError("INTRODUCE_TO is only valid during the Day 1 intros segment")
        if action.target_id is None or action.intent_id is None:
            raise ValueError("INTRODUCE_TO requires target_id and intent_id")
        target = _find_islander(state, action.target_id)
        if target.eliminated or target.id in state.intro_completed_ids:
            raise ValueError(f"intro target is unavailable: {action.model_dump()}")
        if action.intent_id not in _INTRO_INTENT_IDS:
            raise ValueError(f"unknown intro style: {action.intent_id}")
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


_INTRO_INTENT_IDS = {
    "intro_friendly",
    "intro_flirty",
    "intro_deep",
    "intro_banter",
}


def _find_islander(state: GameState, target_id: str) -> IslanderState:
    for islander in state.islanders:
        if islander.id == target_id:
            return islander
    raise ValueError(f"unknown islander: {target_id}")

