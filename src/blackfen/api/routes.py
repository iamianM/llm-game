"""FastAPI router for Blackfen Road."""

from __future__ import annotations

import os
from random import randint
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from src.blackfen.agents.intent import LocalIntentParser
from src.blackfen.agents.narrator import MockNarrator
from src.blackfen.api.models import (
    BlackfenActorView,
    BlackfenItemView,
    BlackfenLocationView,
    BlackfenMonsterView,
    BlackfenNpcView,
    BlackfenPersistedSession,
    BlackfenSessionResponse,
    BlackfenSessionState,
    BlackfenTurnEnvelope,
    BlackfenTurnLogEntry,
    BlackfenTurnResponse,
    BlackfenTurnResponseEnvelope,
    NewBlackfenSessionEnvelope,
    NewBlackfenSessionRequest,
    freeze,
    hydrate,
)
from src.blackfen.content import load_world
from src.blackfen.engine import run_turn
from src.blackfen.hash import state_hash
from src.blackfen.models import GameState
from src.blackfen.new_game import new_game
from src.blackfen.rng import SeededRng

router = APIRouter(prefix="/blackfen", tags=["blackfen"])


@router.post("/session/new", response_model=NewBlackfenSessionEnvelope, status_code=201)
def new_session(req: NewBlackfenSessionRequest) -> NewBlackfenSessionEnvelope:
    seed = req.seed if req.seed is not None else randint(1, 999_999)
    state = new_game(seed, player_name=req.player_name, class_id=req.class_id)
    rng = SeededRng(seed)
    mock = _mock_mode(req.mock_llm)
    session_id = str(uuid4())
    persisted = freeze(state, rng, session_id=session_id, mock_llm=mock)
    return NewBlackfenSessionEnvelope(view=_session_response(session_id, state), persisted=persisted)


@router.post("/session/view", response_model=BlackfenSessionResponse)
def view_session(persisted: BlackfenPersistedSession) -> BlackfenSessionResponse:
    state, _ = hydrate(persisted)
    return _session_response(persisted.session_id, state)


@router.post("/session/turn", response_model=BlackfenTurnResponseEnvelope)
def submit_turn(envelope: BlackfenTurnEnvelope) -> BlackfenTurnResponseEnvelope:
    state, rng = hydrate(envelope.persisted)
    try:
        turn = run_turn(state, envelope.action.text, rng, parser=LocalIntentParser(), narrator=MockNarrator())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": {"code": "INVALID_ACTION", "message": str(exc)}}) from exc
    persisted = freeze(state, rng, session_id=envelope.persisted.session_id, mock_llm=envelope.persisted.mock_llm)
    view = BlackfenTurnResponse(
        state=_state_view(envelope.persisted.session_id, state),
        narration=turn.narration,
        rolls=[roll.model_dump(mode="json") for roll in turn.mechanical_result.rolls],
        suggestions=_suggestions(state),
    )
    return BlackfenTurnResponseEnvelope(view=view, persisted=persisted)


def _session_response(session_id: str, state: GameState) -> BlackfenSessionResponse:
    return BlackfenSessionResponse(session_id=session_id, state=_state_view(session_id, state), suggestions=_suggestions(state))


def _state_view(session_id: str, state: GameState) -> BlackfenSessionState:
    world = load_world()
    location = world.locations[state.current_location_id]
    monsters = []
    if location.encounter is not None:
        for monster in state.active_monsters.get(location.encounter, []):
            monster_def = world.monsters[monster.id]
            monsters.append(BlackfenMonsterView(id=monster.instance_id, name=monster_def.name, image=monster_def.image, hp=monster.hp))
    return BlackfenSessionState(
        session_id=session_id,
        seed=state.seed,
        turn_index=state.turn_index,
        status=state.status,
        state_hash=state_hash(state),
        current_location=_location_view(state.current_location_id),
        known_locations=[_location_view(id_) for id_ in state.known_locations],
        player=BlackfenActorView(id=state.player.id, name=state.player.name, hp=state.player.hp, max_hp=state.player.max_hp, armor_class=state.player.armor_class),
        companion=BlackfenActorView(id=state.companion.id, name=state.companion.name, hp=state.companion.hp, max_hp=state.companion.max_hp, armor_class=state.companion.armor_class),
        companion_stance=state.companion.stance,
        npcs_here=[_npc_view(id_) for id_ in location.npcs],
        monsters_here=monsters,
        inventory=[_item_view(id_) for id_ in state.player.inventory],
        quest_flags=list(state.quest_flags),
        journal=list(state.journal),
        recent_turns=_recent_turns(state),
        last_narration=state.turns[-1].narration if state.turns else None,
    )


def _location_view(location_id: str) -> BlackfenLocationView:
    location = load_world().locations[location_id]
    return BlackfenLocationView(id=location.id, name=location.name, kind=location.kind, image=location.image, description=location.description, exits=list(location.exits), npcs=list(location.npcs))


def _npc_view(npc_id: str) -> BlackfenNpcView:
    npc = load_world().npcs[npc_id]
    return BlackfenNpcView(id=npc.id, name=npc.name, role=npc.role, image=npc.image, disposition=npc.disposition)


def _item_view(item_id: str) -> BlackfenItemView:
    item = load_world().items[item_id]
    return BlackfenItemView(id=item.id, name=item.name, kind=item.kind, image=item.image, description=item.description)


def _recent_turns(state: GameState) -> list[BlackfenTurnLogEntry]:
    return [
        BlackfenTurnLogEntry(
            turn_index=turn.turn_index,
            raw_text=turn.raw_text,
            narration=turn.narration,
            summary=turn.mechanical_result.summary,
            damage_to_player=turn.mechanical_result.damage_to_player,
            damage_to_companion=turn.mechanical_result.damage_to_companion,
            damage_to_enemies=turn.mechanical_result.damage_to_enemies,
            items_gained=list(turn.mechanical_result.items_gained),
            items_lost=list(turn.mechanical_result.items_lost),
        )
        for turn in state.turns[-6:]
    ]


def _suggestions(state: GameState) -> list[str]:
    world = load_world()
    location = world.locations[state.current_location_id]
    suggestions = [f"look around {location.name}"]
    suggestions.extend(f"talk to {world.npcs[id_].name}" for id_ in location.npcs[:2])
    suggestions.extend(f"go {world.locations[id_].name}" for id_ in location.exits[:3])
    if location.encounter is not None and state.active_monsters.get(location.encounter):
        suggestions.insert(0, "attack")
    if state.player.hp < state.player.max_hp:
        suggestions.append("rest")
    return suggestions[:6]


def _mock_mode(override: bool | None = None) -> bool:
    if override is not None:
        return override
    configured = os.environ.get("BLACKFEN_MOCK_LLM")
    if configured is not None:
        return configured != "0"
    return True

