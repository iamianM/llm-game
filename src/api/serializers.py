"""Serialization helpers from engine state to API models."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel

from src.api.display import display
from src.api.models import (
    ApiExchange,
    ApiKnownFact,
    ApiMemory,
    ApiRelationship,
    AudienceState,
    AvailableAction,
    CastDetail,
    CoupleSummary,
    IslanderSummary,
    PlayerState,
    SessionState,
)
from src.game.agents.islander_voice_context import Exchange
from src.game.engine.actions import ActionSpec, available_actions
from src.game.engine.casa_amor import locations_for_villa
from src.game.engine.couples import couple_strength, partner_for
from src.game.engine.daily_recap import humanize_player_reference
from src.game.engine.intents import get_intent
from src.game.engine.results import MechanicalResult
from src.game.state.memory import Memory
from src.game.state.models import FollowUpOption, GameState, IslanderState
from src.game.state.traits import KnownFact


def session_state(session_id: str, state: GameState, recent_delta: int | None = None) -> SessionState:
    """Serialize canonical GameState for the browser."""
    return SessionState(
        session_id=session_id,
        schema_version=state.schema_version,
        seed=state.seed,
        day=state.day,
        phase=state.phase.value,
        phase_label=display(state.phase.value),
        turn_index=state.turn_index,
        location_id=state.location_id.value,
        location_label=display(state.location_id.value),
        villa=state.villa.value,
        villa_label=display(state.villa.value),
        phase_clock=state.phase_clock.model_dump(mode="json"),
        player=PlayerState(
            id=state.player.id,
            name=state.player.name,
            gender=state.player.gender.value,
            archetype_id=state.player.archetype_id,
            public_perception=state.player.public_perception,
            stats=state.player.stats.model_dump(mode="json"),
            memories=[memory_api(memory) for memory in state.player.memories[-12:]],
        ),
        islanders=[islander_summary(state, islander) for islander in state.islanders],
        couples=couple_summaries(state),
        audience=AudienceState(
            public_perception=state.player.public_perception,
            recent_delta=recent_delta,
            trend="rising" if (recent_delta or 0) > 0 else "falling" if (recent_delta or 0) < 0 else "steady",
        ),
        pending_recouple_proposal=(
            None if state.pending_recouple_proposal is None else state.pending_recouple_proposal.model_dump(mode="json")
        ),
        pending_challenge=_pending_challenge_view(state),
        outcome=None if state.outcome is None else state.outcome.value,
        active_conversation_target_id=(
            None if state.active_conversation is None else state.active_conversation.target_id
        ),
        villa_snapshot=villa_snapshot(state),
        daily_recaps=[_recap_view(recap) for recap in state.daily_recaps],
        intros_greetings=dict(state.intros.greetings) if state.intros is not None else {},
    )


def available_actions_api(state: GameState) -> list[AvailableAction]:
    """Serialize available actions with follow-up metadata when present."""
    menu_options = {}
    if state.active_conversation is not None and state.active_conversation.pending_options is not None:
        menu_options = {
            index: option
            for index, option in enumerate(state.active_conversation.pending_options.options)
        }
    return [
        available_action(state, spec, menu_options=menu_options)
        for spec in available_actions(state)
    ]


def available_action(
    state: GameState,
    spec: ActionSpec,
    *,
    menu_options: Mapping[int, FollowUpOption] | None = None,
) -> AvailableAction:
    action = spec.action
    risk: str | None = None
    stat: str | None = None
    hint: Literal["+", "-", ""] = ""
    label = action_label(state, spec)
    description: str | None = None
    if action.kind.value == "respond_with" and action.option_index is not None:
        option = (menu_options or {}).get(action.option_index)
        if option is not None:
            risk = option.risk
            stat = None if option.stat_used is None else display(option.stat_used)
            hint = hide_redundant_hint(state, option.audience_hint)
            label = option.label
            description = display(option.category)
    return AvailableAction(
        kind=action.kind.value,
        label=label,
        target_id=action.target_id,
        intent_id=action.intent_id,
        option_index=action.option_index,
        audience_hint=hint,
        risk=risk,
        stat_used=stat,
        description=description,
        payload=action.payload,
    )


def hide_redundant_hint(state: GameState, hint: Literal["+", "-", ""]) -> Literal["+", "-", ""]:
    """Drop hint chips when Pulse is already pinned at the relevant end of the meter."""
    perception = state.player.public_perception
    if hint == "+" and perception >= 95:
        return ""
    if hint == "-" and perception <= 5:
        return ""
    return hint


def exchange_api(state: GameState, exchange: Exchange | None, speaker_id: str | None) -> ApiExchange | None:
    if exchange is None or speaker_id is None:
        return None
    target = find_name(state, speaker_id)
    data = exchange.model_dump(mode="json")
    return ApiExchange(
        speaker_id=speaker_id,
        speaker_name=target,
        player_dialogue=data["player_dialogue"],
        npc_dialogue=data["npc_dialogue"],
        npc_tone=data["npc_tone"],
        npc_mood_after=data["npc_mood_after"],
    )


def cast_detail(state: GameState, npc_id: str) -> CastDetail:
    islander = next((item for item in state.islanders if item.id == npc_id), None)
    if islander is None:
        raise KeyError(npc_id)
    top = islander.type_on_paper
    familiarity = islander.familiarity_with_player
    return CastDetail(
        id=islander.id,
        name=islander.name,
        gender=islander.gender.value,
        archetype=islander.archetype,
        mood=islander.mood.value,
        location=display(islander.location_id.value),
        backstory=islander.backstory,
        familiarity=familiarity,
        relationship=ApiRelationship(**islander.relationship.model_dump(mode="json")),
        type_on_paper={
            "physical_type": top.physical_type if familiarity >= 25 else None,
            "personality_type": top.personality_type if familiarity >= 50 else None,
            "values": top.values if familiarity >= 75 else None,
            "dealbreakers": top.dealbreakers if familiarity >= 100 else None,
        },
        known_facts=known_facts_api(state, islander.id),
        memories=[memory_api(memory) for memory in islander.memories[-12:]],
        coupled_with=partner_id(state, islander.id),
        eliminated=islander.eliminated,
    )


def couple_summaries(state: GameState) -> list[CoupleSummary]:
    return [
        CoupleSummary(
            partner_a_id=couple.partner_a_id,
            partner_b_id=couple.partner_b_id,
            partner_a_name=find_name(state, couple.partner_a_id),
            partner_b_name=find_name(state, couple.partner_b_id),
            strength=couple_strength(state, couple),
            formed_on_day=couple.formed_on_day,
            formed_via=couple.formed_via,
            formed_via_label=display(couple.formed_via),
            rebound=couple.rebound,
            is_player_couple="player" in {couple.partner_a_id, couple.partner_b_id},
        )
        for couple in state.couples
    ]


def memory_api(memory: Memory) -> ApiMemory:
    data = memory.model_dump(mode="json")
    return ApiMemory(
        id=data["id"],
        holder_id=data["holder_id"],
        subject_id=data["subject_id"],
        content=data["content"],
        emotional_weight=data["emotional_weight"],
        source=data["source"],
        tags=list(data.get("tags") or []),
        formed_on_turn=int(data.get("formed_on_turn") or 0),
    )


def known_facts_api(state: GameState, npc_id: str) -> list[ApiKnownFact]:
    """Serialize player-known facts about one NPC."""
    facts = [
        fact for fact in state.player.known_facts.values()
        if fact.fact_key.startswith(f"{npc_id}.")
    ]
    facts.sort(key=lambda fact: (fact.source != "direct", fact.fact_key))
    return [_known_fact_api(fact) for fact in facts]


def _known_fact_api(fact: KnownFact) -> ApiKnownFact:
    trait_key = fact.fact_key.split(".", 1)[1] if "." in fact.fact_key else fact.fact_key
    group: Literal["confirmed", "heard", "trivia"] = (
        "confirmed" if fact.source in {"direct", "social_event"} else "heard"
    )
    if trait_key not in {
        "occupation",
        "hometown",
        "age",
        "favorite_food",
        "hobby",
        "drink_of_choice",
        "biggest_fear",
        "love_language",
        "worst_habit",
        "pet_peeve",
        "insecurity",
        "past_heartbreak",
        "hidden_secret",
    }:
        group = "trivia"
    return ApiKnownFact(
        fact_key=fact.fact_key,
        label=trait_key.replace("_", " ").title(),
        value=fact.value,
        source=fact.source,
        source_npc_id=fact.source_npc_id,
        confidence=fact.confidence,
        citation=fact.citation,
        group=group,
    )


def villa_snapshot(state: GameState) -> dict[str, list[str]]:
    snapshot: dict[str, list[str]] = {}
    for location in locations_for_villa(state.villa):
        occupants = ["You"] if location is state.location_id else []
        occupants.extend(
            islander.name for islander in state.islanders if islander.location_id is location and not islander.eliminated
        )
        snapshot[display(location.value)] = occupants
    return snapshot


def islander_summary(state: GameState, islander: IslanderState) -> IslanderSummary:
    return IslanderSummary(
        id=islander.id,
        name=islander.name,
        gender=islander.gender.value,
        archetype=islander.archetype,
        mood=islander.mood.value,
        location_id=islander.location_id.value,
        location_label=display(islander.location_id.value),
        eliminated=islander.eliminated,
        coupled=partner_id(state, islander.id) is not None,
        familiarity_with_player=islander.familiarity_with_player,
    )


def partner_id(state: GameState, actor_id: str) -> str | None:
    for couple in state.couples:
        if actor_id in {couple.partner_a_id, couple.partner_b_id}:
            return partner_for(couple, actor_id)
    return None


def find_name(state: GameState, actor_id: str) -> str:
    if actor_id == "player":
        return state.player.name
    for islander in state.islanders:
        if islander.id == actor_id:
            return islander.name
    return actor_id


def action_label(state: GameState, spec: ActionSpec) -> str:
    """Render action labels from structured action/state fields."""
    action = spec.action
    if action.kind.value == "join_gather" and state.pending_gather is not None:
        return f"Join everyone at {display(state.pending_gather.gather_location.value)}"
    if action.kind.value == "challenge_response" and state.pending_challenge is not None:
        # Round-based minigames: the engine label is "Quiz rN/M: <choice>".
        # The browser renders the round counter + question stem in a panel
        # above the menu (see GameStage.QuizHeader), so strip the redundant
        # round prefix here and surface just the choice text on the card;
        # otherwise the buttons read as a bag of fragments with no question.
        from src.game.engine.challenges import ROUND_BASED_MINIGAMES
        if state.pending_challenge.kind in ROUND_BASED_MINIGAMES:
            label = spec.label
            if ":" in label:
                label = label.split(":", 1)[1].strip()
            return label
        target = "" if action.target_id is None else f": choose {find_name(state, action.target_id)}"
        return f"{display(state.pending_challenge.kind)}{target}"
    if action.kind.value == "recouple" and action.target_id is not None:
        # During a pending recoupling ceremony, the engine already emits a
        # specific label ("Stay with X" or "Couple with Y") that distinguishes
        # the player's current partner from a swap. Keep it.
        if (
            state.pending_gather is not None
            and state.pending_gather.kind == "ceremony"
            and state.pending_gather.event_id.startswith("recoupling")
        ):
            return spec.label
        return f"Pair with {find_name(state, action.target_id)}"
    if action.kind.value == "propose_recouple" and action.target_id is not None:
        return f"Ask {find_name(state, action.target_id)} for a Heart Swap"
    if action.kind.value == "npc_proposal_response" and action.target_id is not None:
        proposer = find_name(state, action.target_id)
        if action.intent_id == "accept":
            return f"Accept {proposer}'s Heart Swap proposal"
        if action.intent_id == "decline_politely":
            return f"Decline {proposer} politely"
        if action.intent_id == "decline_harshly":
            return f"Decline {proposer} harshly"
    if action.kind.value == "hideaway":
        partner_id = partner_id_for_player(state)
        suffix = "" if partner_id is None else f" with {find_name(state, partner_id)}"
        return f"Spend the night in {display('hideaway')}{suffix}"
    if action.kind.value == "casa_decision":
        if action.intent_id == "return_with_original":
            return "Return loyal"
        if action.intent_id == "return_with_new" and action.target_id is not None:
            return f"Return with {find_name(state, action.target_id)}"
        if action.intent_id == "return_single":
            return "Return solo"
    if action.kind.value == "move" and action.target_id is not None:
        return f"Move to {display(action.target_id)}"
    if action.kind.value == "introduce_to" and action.target_id is not None:
        verb = {
            "intro_friendly": "Be friendly with",
            "intro_flirty": "Flirt with",
            "intro_deep": "Get deep with",
            "intro_banter": "Banter with",
        }.get(action.intent_id or "", "Greet")
        return f"{verb} {find_name(state, action.target_id)}"
    if action.kind.value == "start_conversation" and action.target_id is not None:
        name = find_name(state, action.target_id)
        # Free-time openers carry an intent_id; surface the opener line so the
        # label is self-contained in the bottom fan / LLM decider. The web
        # CharacterMenu strips the "Talk to {name} — " prefix and shows just
        # the opener inside the matching category branch.
        if action.intent_id is not None:
            try:
                opener = get_intent(action.intent_id).label
            except ValueError:
                opener = None
            if opener:
                return f"Talk to {name} — {opener}"
        return f"Talk to {name}"
    if action.kind.value == "end_conversation":
        return "Walk away"
    return spec.label


def audience_delta(result: MechanicalResult) -> int | None:
    return result.audience_delta if result.audience_delta != 0 else None


def _model_dump(value: BaseModel) -> dict[str, object]:
    return value.model_dump(mode="json")


def _recap_view(recap: BaseModel) -> dict[str, object]:
    """Serialize a daily recap, humanizing any "the player" label for the reader.

    Recaps are surfaced verbatim from islander memories, which are written in a
    name-agnostic voice ("the player"). The recap is read *by* the player, so we
    rewrite that label to second person at the view boundary. This also cleans
    recaps already baked into older checkpoints, where the substitution could
    not have run at generation time.
    """
    data = _model_dump(recap)
    items = data.get("items")
    if isinstance(items, list):
        for item in items:
            content = item.get("content") if isinstance(item, dict) else None
            if isinstance(content, str):
                item["content"] = humanize_player_reference(content)
    return data


def partner_id_for_player(state: GameState) -> str | None:
    return partner_id(state, "player")


def _pending_challenge_view(state: GameState) -> dict[str, object] | None:
    """Browser-facing view of a round-based pending minigame.

    Returns a compact dict (kind, current round + stem + tier + choices) for
    round-based minigames so the browser can render the question text above
    the choice list. Legacy single-roll challenges return ``None`` because
    they have no per-round state.
    """
    from src.game.engine.challenges import ROUND_BASED_MINIGAMES
    challenge = state.pending_challenge
    if challenge is None:
        return None
    if challenge.kind not in ROUND_BASED_MINIGAMES:
        return None
    cur_index = challenge.current_round_index

    def _round_view(round_) -> dict[str, object]:
        chosen = next((c for c in round_.choices if c.id == round_.chosen_id), None)
        correct = next((c for c in round_.choices if c.is_correct), None)
        reaction_line: str | None = None
        for reveal in round_.reveals:
            if reveal.kind == "reaction":
                line = reveal.payload.get("line")
                if isinstance(line, str):
                    reaction_line = line
                    break
        return {
            "round_index": round_.index,
            "stem": round_.stem,
            "chosen_label": chosen.label if chosen else None,
            "correct_label": correct.label if correct else None,
            "is_correct": bool(chosen and chosen.is_correct),
            "points": round_.points,
            "reaction_line": reaction_line,
        }

    answered = [_round_view(r) for r in challenge.rounds if r.chosen_id is not None]
    if cur_index >= len(challenge.rounds):
        return {
            "kind": challenge.kind,
            "finished": True,
            "classification": challenge.classification,
            "total_points": challenge.total_points,
            "audience_delta": challenge.audience_delta,
            "round_count": len(challenge.rounds),
            "answered_rounds": answered,
        }
    current = challenge.rounds[cur_index]
    return {
        "kind": challenge.kind,
        "finished": False,
        "round_index": cur_index,
        "round_count": len(challenge.rounds),
        "stem": current.stem,
        "trait_key": current.trait_key,
        "tier": current.tier,
        "mechanical": current.mechanical,
        "target_id": current.target_id,
        "answered_rounds": answered,
    }

