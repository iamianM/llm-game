"""FastAPI app for Paradise Hearts."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path
from random import randint

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from src.api.display import translate_text
from src.api.models import (
    ApiError,
    ApiErrorBody,
    CastDetail,
    CouplesResponse,
    NewSessionRequest,
    SessionResponse,
    TurnRequest,
    TurnResponse,
    VersionResponse,
)
from src.api.serializers import (
    audience_delta,
    available_actions_api,
    cast_detail,
    couple_summaries,
    exchange_api,
    session_state,
)
from src.api.session import AgentBundle, GameSession, add_session, delete_session, get_session
from src.api.streaming import chunk_text, sse
from src.game.agents.trait_generator import (
    OpenAITraitGenerator,
    assign_trait_cards,
    opening_generation_seeds,
)
from src.game.engine.actions import PlayerAction
from src.game.engine.character_creation import DEFAULT_ARCHETYPE_STATS, create_character
from src.game.engine.intents import available_intents_for
from src.game.engine.turn import TurnResult, run_turn
from src.game.state.models import SCHEMA_VERSION, Gender, new_game
from src.game.state.rng import SeededRng
from src.game.state.snapshot import state_hash, state_hash_payload

app = FastAPI(title="Paradise Hearts API", version="0.1.0")
logger = logging.getLogger("paradise.api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(schema_version=SCHEMA_VERSION, api_version="0.1.0", build="2026-05-14")


@app.post("/session/new", response_model=SessionResponse, status_code=201)
def new_session(req: NewSessionRequest) -> SessionResponse:
    seed = req.seed if req.seed is not None else randint(1, 999_999)
    state = new_game(seed)
    if not _mock_mode(req.mock_llm):
        try:
            generator = OpenAITraitGenerator()
            assign_trait_cards(state.islanders, generator.generate_opening_cast(opening_generation_seeds(state.islanders)))
        except Exception as exc:
            raise _http_error(
                502,
                "STORY_ENGINE_ERROR",
                "Real mode could not open Sunset Bay. Check that OPENAI_API_KEY is set and restart the API server.",
            ) from exc
    state.player.name = req.player_name or "You"
    try:
        create_character(
            state,
            archetype_id=req.archetype,
            gender=Gender(req.player_gender),
            stats=DEFAULT_ARCHETYPE_STATS[req.archetype],
        )
    except ValueError as exc:
        raise _http_error(400, "VALIDATION_ERROR", str(exc)) from exc
    agents = AgentBundle.mock() if _mock_mode(req.mock_llm) else AgentBundle.live()
    session = add_session(state, SeededRng(seed), agents)
    return SessionResponse(
        session_id=session.session_id,
        state=session_state(session.session_id, session.state),
        available_actions=available_actions_api(session.state),
    )


@app.get("/session/{session_id}", response_model=SessionResponse)
def get_state(session_id: str) -> SessionResponse:
    session = _session_or_404(session_id)
    return SessionResponse(
        session_id=session.session_id,
        state=session_state(session.session_id, session.state),
        available_actions=available_actions_api(session.state),
    )


@app.post("/session/{session_id}/turn", response_model=TurnResponse)
async def submit_turn(session_id: str, req: TurnRequest) -> TurnResponse:
    session = _session_or_404(session_id)
    async with session.lock:
        try:
            turn = await asyncio.to_thread(_run_turn, session, req)
        except ValueError as exc:
            raise _http_error(400, "INVALID_ACTION", str(exc)) from exc
    return _turn_response(session.session_id, turn)


@app.post("/session/{session_id}/turn/stream")
async def submit_turn_stream(session_id: str, req: TurnRequest) -> StreamingResponse:
    session = _session_or_404(session_id)

    async def events() -> AsyncIterator[str]:
        async with session.lock:
            try:
                turn = await asyncio.to_thread(_run_turn, session, req)
            except ValueError as exc:
                yield sse("error", {"status": 400, "message": str(exc)}, event_id=0)
                return
        response = _turn_response(session.session_id, turn)
        exchange = response.exchange
        yield sse("turn_start", {"turn": turn.state.turn_index, "phase": turn.state.phase.value}, event_id=1)
        if exchange is not None:
            yield sse("dialogue_start", {"speaker": _exchange_speaker_id(turn), "speaker_name": exchange.speaker_name}, event_id=2)
            async for chunk in chunk_text(exchange.npc_dialogue):
                yield sse("dialogue_chunk", {"text": chunk})
            yield sse("dialogue_end", {"mood_after": exchange.npc_mood_after}, event_id=3)
        yield sse("state", session_state(session.session_id, turn.state).model_dump(mode="json"), event_id=4)
        yield sse("options", {"actions": [a.model_dump(mode="json") for a in available_actions_api(turn.state)]}, event_id=5)
        if turn.ceremony_events:
            yield sse("ceremony", {"events": [e.model_dump(mode="json") for e in turn.ceremony_events]}, event_id=6)
        yield sse("response", response.model_dump(mode="json"), event_id=7)
        yield sse("turn_end", {"state_hash": turn.state_hash}, event_id=8)

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/session/{session_id}/cast/{npc_id}", response_model=CastDetail)
def get_cast(session_id: str, npc_id: str) -> CastDetail:
    session = _session_or_404(session_id)
    try:
        return cast_detail(session.state, npc_id)
    except KeyError as exc:
        raise _http_error(404, "NOT_FOUND", f"unknown Heartbreaker: {npc_id}") from exc


@app.get("/session/{session_id}/couples", response_model=CouplesResponse)
def get_couples(session_id: str) -> CouplesResponse:
    session = _session_or_404(session_id)
    coupled_ids = {actor for couple in session.state.couples for actor in (couple.partner_a_id, couple.partner_b_id)}
    singles = [item.id for item in session.state.islanders if not item.eliminated and item.id not in coupled_ids]
    return CouplesResponse(couples=couple_summaries(session.state), singles=singles)


@app.get("/session/{session_id}/timeline")
def get_timeline(session_id: str) -> dict[str, object]:
    session = _session_or_404(session_id)
    return {"days": [recap.model_dump(mode="json") for recap in session.state.daily_recaps]}


@app.delete("/session/{session_id}", status_code=204)
def end_session(session_id: str) -> Response:
    delete_session(session_id)
    return Response(status_code=204)


def _run_turn(session: GameSession, req: TurnRequest) -> TurnResult:
    action = PlayerAction.model_validate(req.model_dump(exclude_none=True))
    if action.kind.value == "start_conversation" and action.target_id and action.intent_id is None:
        intents = available_intents_for(session.state, action.target_id)
        if intents:
            action.intent_id = intents[0].id
    input_hash = state_hash(state_hash_payload(session.state))
    turn = run_turn(
        session.state,
        action,
        session.rng,
        islander_voice=session.agents.islander_voice,
        contextual_options=session.agents.contextual_options,
        event_narrator=session.agents.event_narrator,
        conversation_curator=session.agents.conversation_curator,
        villa_orchestrator=session.agents.villa_orchestrator,
        background_dialogue=session.agents.background_dialogue,
    )
    session.state = turn.state
    session.records.append({"input_hash": input_hash, "output_hash": turn.state_hash})
    logger.info(
        "turn session=%s turn=%s day=%s phase=%s action=%s target=%s intent=%s exchange=%s events=%s active=%s hash=%s",
        session.session_id,
        turn.state.turn_index,
        turn.state.day,
        turn.state.phase.value,
        action.kind.value,
        action.target_id,
        action.intent_id,
        None if turn.exchange is None else _exchange_speaker_id(turn),
        ",".join(str(event.kind) for event in turn.ceremony_events) or "-",
        turn.state.active_conversation.target_id if turn.state.active_conversation else None,
        turn.state_hash,
    )
    return turn


def _turn_response(session_id: str, turn: TurnResult) -> TurnResponse:
    result = turn.mechanical_result
    return TurnResponse(
        state=session_state(session_id, turn.state, audience_delta(result)),
        exchange=exchange_api(turn.state, turn.exchange, result.action.target_id),
        available_actions=available_actions_api(turn.state),
        ceremony_events=[_translated_dump(event) for event in turn.ceremony_events],
        event_narration=None if turn.event_narration is None else _translated_dump(turn.event_narration),
        audience_delta=audience_delta(result),
        audience_delta_reason=None if result.audience_reason is None else translate_text(result.audience_reason),
        memories_formed=[_translated_dump(batch) for batch in turn.curator_batches],
        background_activity=[_translated_dump(dialogue) for dialogue in turn.agent_commits.background_dialogues],
        state_hash=turn.state_hash,
    )


def _exchange_speaker_id(turn: TurnResult) -> str | None:
    if turn.exchange is None:
        return None
    return turn.mechanical_result.action.target_id


def _session_or_404(session_id: str) -> GameSession:
    session = get_session(session_id)
    if session is None:
        raise _http_error(404, "SESSION_NOT_FOUND", f"session not found: {session_id}")
    return session


def _http_error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail=ApiError(error=ApiErrorBody(code=code, message=message)).model_dump())


def _mock_mode(override: bool | None = None) -> bool:
    if override is not None:
        return override
    return os.environ.get("PARADISE_MOCK_LLM", "1") != "0"


def _load_local_env() -> None:
    """Load local secrets for desktop development without printing them."""
    env_path = Path(".env.local")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env()


def _translated_dump(value: BaseModel) -> dict[str, object]:
    data = value.model_dump(mode="json")
    return {key: translate_text(item) if isinstance(item, str) else item for key, item in data.items()}
