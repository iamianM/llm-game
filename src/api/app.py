"""FastAPI app for Paradise Hearts.

The API is stateless. Every endpoint that touches game state takes the full
``PersistedSession`` envelope in the request body and returns the updated
envelope alongside the renderable view. The client owns persistence — today
that's localStorage, tomorrow it's a Postgres ``game_history`` table indexed by
``user_id``. The server itself stores nothing across requests.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path
from random import randint
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.api.checkpoints import (
    CheckpointSummary,
    list_checkpoints,
    load_named_checkpoint_payload,
)
from src.api.models import (
    ApiError,
    ApiErrorBody,
    CastDetail,
    CastRequest,
    CheckpointListResponse,
    CheckpointStartRequest,
    CheckpointSummaryResponse,
    NewSessionEnvelope,
    NewSessionRequest,
    SessionResponse,
    TurnEnvelope,
    TurnResponse,
    TurnResponseEnvelope,
    VersionResponse,
)
from src.api.persisted import PersistedSession, freeze, hydrate
from src.api.serializers import (
    audience_delta,
    available_actions_api,
    cast_detail,
    exchange_api,
    session_state,
)
from src.api.session import AgentBundle
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
from src.game.state.models import SCHEMA_VERSION, GameState, Gender, new_game
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

# Routes are mounted at the root. On Vercel, the `routePrefix: "/api"` in
# vercel.json places this whole app behind `/api/*` from the browser's view;
# Vercel strips that prefix before invoking FastAPI, so the routes here stay
# at root. Locally, the FastAPI dev server is reached at `localhost:8000/...`.


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(schema_version=SCHEMA_VERSION, api_version="0.1.0", build="2026-05-19")


@app.post("/session/new", response_model=NewSessionEnvelope, status_code=201)
def new_session(req: NewSessionRequest) -> NewSessionEnvelope:
    seed = req.seed if req.seed is not None else randint(1, 999_999)
    state = new_game(seed)
    mock = _mock_mode(req.mock_llm)
    if not mock:
        try:
            generator = OpenAITraitGenerator()
            assign_trait_cards(state.islanders, generator.generate_opening_cast(opening_generation_seeds(state.islanders)))
        except Exception as exc:
            logger.exception("real-mode trait generation failed")
            raise _http_error(
                502,
                "STORY_ENGINE_ERROR",
                f"Real mode could not open Sunset Bay; the story engine raised {type(exc).__name__}.",
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
    rng = SeededRng(seed)
    session_id = str(uuid4())
    persisted = freeze(state, rng, session_id=session_id, user_id=None, mock_llm=mock)
    view = SessionResponse(
        session_id=session_id,
        state=session_state(session_id, state),
        available_actions=available_actions_api(state),
    )
    return NewSessionEnvelope(view=view, persisted=persisted)


@app.get("/checkpoints", response_model=CheckpointListResponse)
def checkpoints() -> CheckpointListResponse:
    """Return loadable saved-state options for the main-menu picker."""
    return CheckpointListResponse(
        checkpoints=[
            CheckpointSummaryResponse(
                name=ck.name,
                label=ck.label,
                day=ck.day,
                phase=ck.phase,
                source=ck.source,
            )
            for ck in list_checkpoints()
        ]
    )


@app.post("/session/from-checkpoint", response_model=NewSessionEnvelope, status_code=201)
def session_from_checkpoint(req: CheckpointStartRequest) -> NewSessionEnvelope:
    """Open a new session preloaded from a saved checkpoint.

    The on-the-wire shape matches `POST /session/new` so the client can route
    to the same `/play/[sessionId]` page after either path. The new
    ``session_id`` is freshly minted (the checkpoint's own session_id is
    intentionally not reused — multiple branches can spring off one save).
    """
    try:
        payload = load_named_checkpoint_payload(req.name)
    except KeyError as exc:
        raise _http_error(
            404,
            "CHECKPOINT_NOT_FOUND",
            f"No loadable checkpoint named {req.name!r} (it may be missing "
            "or saved at an older schema version).",
        ) from exc
    state_payload = payload["state"]
    if not isinstance(state_payload, dict):
        raise _http_error(500, "CHECKPOINT_CORRUPT", "checkpoint state missing or not an object")
    state = GameState.model_validate(state_payload)
    seed = payload.get("seed")
    if not isinstance(seed, int):
        raise _http_error(500, "CHECKPOINT_CORRUPT", "checkpoint missing seed")
    rng_state = payload.get("rng_state")
    if isinstance(rng_state, list):
        rng = SeededRng.from_snapshot(seed, rng_state)
    else:
        rng = SeededRng(seed)
    mock = _mock_mode(req.mock_llm)
    session_id = str(uuid4())
    persisted = freeze(state, rng, session_id=session_id, user_id=None, mock_llm=mock)
    view = SessionResponse(
        session_id=session_id,
        state=session_state(session_id, state),
        available_actions=available_actions_api(state),
    )
    return NewSessionEnvelope(view=view, persisted=persisted)


@app.post("/session/view", response_model=SessionResponse)
def view_session(persisted: PersistedSession) -> SessionResponse:
    state, _ = hydrate(persisted)
    return SessionResponse(
        session_id=persisted.session_id,
        state=session_state(persisted.session_id, state),
        available_actions=available_actions_api(state),
    )


@app.post("/session/turn", response_model=TurnResponseEnvelope)
async def submit_turn(envelope: TurnEnvelope) -> TurnResponseEnvelope:
    state, rng = hydrate(envelope.persisted)
    agents = _agents_for(envelope.persisted.mock_llm)
    try:
        turn = await asyncio.to_thread(_run_turn, state, rng, envelope, agents)
    except ValueError as exc:
        raise _http_error(400, "INVALID_ACTION", str(exc)) from exc
    new_persisted = freeze(
        turn.state,
        rng,
        session_id=envelope.persisted.session_id,
        user_id=envelope.persisted.user_id,
        mock_llm=envelope.persisted.mock_llm,
    )
    return TurnResponseEnvelope(view=_turn_response(envelope.persisted.session_id, turn), persisted=new_persisted)


@app.post("/session/turn/stream")
async def submit_turn_stream(envelope: TurnEnvelope) -> StreamingResponse:
    state, rng = hydrate(envelope.persisted)
    agents = _agents_for(envelope.persisted.mock_llm)
    session_id = envelope.persisted.session_id

    async def events() -> AsyncIterator[str]:
        try:
            turn = await asyncio.to_thread(_run_turn, state, rng, envelope, agents)
        except ValueError as exc:
            yield sse("error", {"status": 400, "message": str(exc)}, event_id=0)
            return
        new_persisted = freeze(
            turn.state,
            rng,
            session_id=session_id,
            user_id=envelope.persisted.user_id,
            mock_llm=envelope.persisted.mock_llm,
        )
        view = _turn_response(session_id, turn)
        exchange = view.exchange
        yield sse("turn_start", {"turn": turn.state.turn_index, "phase": turn.state.phase.value}, event_id=1)
        if exchange is not None:
            yield sse("dialogue_start", {"speaker": _exchange_speaker_id(turn), "speaker_name": exchange.speaker_name}, event_id=2)
            async for chunk in chunk_text(exchange.npc_dialogue):
                yield sse("dialogue_chunk", {"text": chunk})
            yield sse("dialogue_end", {"mood_after": exchange.npc_mood_after}, event_id=3)
        yield sse("state", session_state(session_id, turn.state).model_dump(mode="json"), event_id=4)
        yield sse("options", {"actions": [a.model_dump(mode="json") for a in available_actions_api(turn.state)]}, event_id=5)
        if turn.ceremony_events:
            yield sse("ceremony", {"events": [e.model_dump(mode="json") for e in turn.ceremony_events]}, event_id=6)
        envelope_out = TurnResponseEnvelope(view=view, persisted=new_persisted)
        yield sse("response", envelope_out.model_dump(mode="json"), event_id=7)
        yield sse("turn_end", {"state_hash": turn.state_hash}, event_id=8)

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/session/cast", response_model=CastDetail)
def get_cast(req: CastRequest) -> CastDetail:
    state, _ = hydrate(req.persisted)
    try:
        return cast_detail(state, req.npc_id)
    except KeyError as exc:
        raise _http_error(404, "NOT_FOUND", f"unknown Heartbreaker: {req.npc_id}") from exc


def _run_turn(state: GameState, rng: SeededRng, envelope: TurnEnvelope, agents: AgentBundle) -> TurnResult:
    action = PlayerAction.model_validate(envelope.action.model_dump(exclude_none=True))
    if action.kind.value == "start_conversation" and action.target_id and action.intent_id is None:
        intents = available_intents_for(state, action.target_id)
        if intents:
            action.intent_id = intents[0].id
    input_hash = state_hash(state_hash_payload(state))
    turn = run_turn(
        state,
        action,
        rng,
        islander_voice=agents.islander_voice,
        contextual_options=agents.contextual_options,
        event_narrator=agents.event_narrator,
        conversation_curator=agents.conversation_curator,
        villa_orchestrator=agents.villa_orchestrator,
        background_dialogue=agents.background_dialogue,
    )
    logger.info(
        "turn session=%s turn=%s day=%s phase=%s action=%s target=%s intent=%s exchange=%s events=%s active=%s hash=%s input_hash=%s",
        envelope.persisted.session_id,
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
        input_hash,
    )
    return turn


def _turn_response(session_id: str, turn: TurnResult) -> TurnResponse:
    result = turn.mechanical_result
    return TurnResponse(
        state=session_state(session_id, turn.state, audience_delta(result)),
        exchange=exchange_api(turn.state, turn.exchange, result.action.target_id),
        available_actions=available_actions_api(turn.state),
        ceremony_events=[_model_dump(event) for event in turn.ceremony_events],
        event_narration=None if turn.event_narration is None else _model_dump(turn.event_narration),
        audience_delta=audience_delta(result),
        audience_delta_reason=result.audience_reason,
        memories_formed=[_model_dump(batch) for batch in turn.curator_batches],
        background_activity=[_model_dump(dialogue) for dialogue in turn.agent_commits.background_dialogues],
        state_hash=turn.state_hash,
    )


def _exchange_speaker_id(turn: TurnResult) -> str | None:
    if turn.exchange is None:
        return None
    return turn.mechanical_result.action.target_id


def _http_error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail=ApiError(error=ApiErrorBody(code=code, message=message)).model_dump())


def _agents_for(mock_llm: bool) -> AgentBundle:
    return AgentBundle.mock() if _mock_mode(mock_llm) else AgentBundle.live()


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


def _model_dump(value: BaseModel) -> dict[str, object]:
    return value.model_dump(mode="json")
