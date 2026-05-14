"""Serialization helpers from engine state to API models."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel

from src.api.display import display, translate_text
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
        outcome=None if state.outcome is None else state.outcome.value,
        active_conversation_target_id=(
            None if state.active_conversation is None else state.active_conversation.target_id
        ),
        villa_snapshot=villa_snapshot(state),
        daily_recaps=[_translated_dump(recap) for recap in state.daily_recaps],
    )


def available_actions_api(state: GameState) -> list[AvailableAction]:
    """Serialize available actions with follow-up metadata when present."""
    menu_options = {}
    if state.active_conversation is not None and state.active_conversation.pending_options is not None:
        menu_options = {
            index: option
            for index, option in enumerate(state.active_conversation.pending_options.options)
        }
    return [available_action(spec, menu_options=menu_options) for spec in available_actions(state)]


def available_action(
    spec: ActionSpec,
    *,
    menu_options: Mapping[int, FollowUpOption] | None = None,
) -> AvailableAction:
    action = spec.action
    risk: str | None = None
    stat: str | None = None
    hint: Literal["+", "-", ""] = ""
    if action.kind.value == "respond_with" and action.option_index is not None:
        option = (menu_options or {}).get(action.option_index)
        if option is not None:
            risk = option.risk
            stat = None if option.stat_used is None else display(option.stat_used)
            hint = option.audience_hint
    return AvailableAction(
        kind=action.kind.value,
        label=translate_label(spec.label),
        target_id=action.target_id,
        intent_id=action.intent_id,
        option_index=action.option_index,
        audience_hint=hint,
        risk=risk,
        stat_used=stat,
        description=None,
    )


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
        holder_id=data["holder_id"],
        subject_id=data["subject_id"],
        content=translate_text(data["content"]),
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
        value=translate_text(fact.value),
        source=fact.source,
        source_npc_id=fact.source_npc_id,
        confidence=fact.confidence,
        citation=translate_text(fact.citation),
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


def translate_label(label: str) -> str:
    translated = translate_text(label).replace("Snog Marry Pie", "Kiss Wed Pass")
    if translated.startswith("Initial couple with "):
        return translated.replace("Initial couple with ", "Pair with ", 1)
    if ": " in translated and translated.endswith(" introduction"):
        name, rest = translated.split(": ", 1)
        dynamic = rest.removesuffix(" introduction").strip().lower()
        return f"Spark {dynamic} with {name}"
    return translated


def audience_delta(result: MechanicalResult) -> int | None:
    return result.audience_delta if result.audience_delta != 0 else None


def _translated_dump(value: BaseModel) -> dict[str, object]:
    data = value.model_dump(mode="json")
    return {key: translate_text(item) if isinstance(item, str) else item for key, item in data.items()}
