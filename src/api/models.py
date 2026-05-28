"""Pydantic models for the Paradise Hearts HTTP API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.api.persisted import PersistedSession


class ApiErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ApiErrorBody


class NewSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archetype: Literal["heartthrob", "class_clown", "loyal_friend"]
    player_name: str = "You"
    player_gender: Literal["man", "woman"] = "man"
    seed: int | None = None
    mock_llm: bool | None = None


class CheckpointSummaryResponse(BaseModel):
    """One main-menu entry for a loadable saved state."""

    model_config = ConfigDict(extra="forbid")

    name: str
    label: str
    day: int
    phase: str
    source: Literal["bundled", "local"]


class CheckpointListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checkpoints: list[CheckpointSummaryResponse]


class CheckpointStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    mock_llm: bool | None = None


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: str
    target_id: str | None = None
    intent_id: str | None = None
    option_index: int | None = None
    payload: dict[str, object] | None = None


class ApiRelationship(BaseModel):
    affection: int
    chemistry: int
    trust: int
    friendship: int


class ApiMemory(BaseModel):
    id: str
    holder_id: str
    subject_id: str
    content: str
    emotional_weight: int
    source: str
    tags: list[str]
    formed_on_turn: int


class ApiKnownFact(BaseModel):
    fact_key: str
    label: str
    value: str
    source: str
    source_npc_id: str | None
    confidence: float
    citation: str
    group: Literal["confirmed", "heard", "trivia"]


class PlayerState(BaseModel):
    id: str
    name: str
    gender: str
    archetype_id: str
    public_perception: int
    stats: dict[str, int]
    memories: list[ApiMemory]


class IslanderSummary(BaseModel):
    id: str
    name: str
    gender: str
    archetype: str
    mood: str
    location_id: str
    location_label: str
    eliminated: bool
    coupled: bool
    familiarity_with_player: int


class CoupleSummary(BaseModel):
    partner_a_id: str
    partner_b_id: str
    partner_a_name: str
    partner_b_name: str
    strength: int
    formed_on_day: int
    formed_via: str
    formed_via_label: str
    rebound: bool
    is_player_couple: bool


class AudienceState(BaseModel):
    public_perception: int
    recent_delta: int | None
    trend: Literal["rising", "falling", "steady"]


class AvailableAction(BaseModel):
    kind: str
    label: str
    target_id: str | None
    intent_id: str | None
    option_index: int | None
    audience_hint: Literal["+", "-", ""]
    risk: str | None
    stat_used: str | None
    payload: dict[str, object] | None = None
    description: str | None = None


class ApiExchange(BaseModel):
    speaker_id: str
    speaker_name: str
    player_dialogue: str
    npc_dialogue: str
    npc_tone: str
    npc_mood_after: str


class SessionState(BaseModel):
    session_id: str
    schema_version: int
    seed: int
    day: int
    phase: str
    phase_label: str
    turn_index: int
    location_id: str
    location_label: str
    villa: str
    villa_label: str
    phase_clock: dict[str, object]
    player: PlayerState
    islanders: list[IslanderSummary]
    couples: list[CoupleSummary]
    audience: AudienceState
    pending_recouple_proposal: dict[str, object] | None
    pending_challenge: dict[str, object] | None = None
    outcome: str | None
    active_conversation_target_id: str | None
    villa_snapshot: dict[str, list[str]]
    daily_recaps: list[dict[str, object]]
    # Dynamically-generated NPC greetings keyed by islander id. Empty in mock
    # mode; the UI falls back to templated greetings in web/lib/intros.ts.
    intros_greetings: dict[str, str] = {}


class SessionResponse(BaseModel):
    session_id: str
    state: SessionState
    available_actions: list[AvailableAction]


class TurnResponse(BaseModel):
    state: SessionState
    exchange: ApiExchange | None
    available_actions: list[AvailableAction]
    ceremony_events: list[dict[str, object]]
    event_narration: dict[str, object] | None
    audience_delta: int | None
    audience_delta_reason: str | None
    memories_formed: list[dict[str, object]]
    background_activity: list[dict[str, object]]
    state_hash: str


class NewSessionEnvelope(BaseModel):
    """Initial session payload: a renderable view plus the blob the client persists."""

    view: SessionResponse
    persisted: PersistedSession


class TurnEnvelope(BaseModel):
    """Stateless turn request: client sends the full persisted blob plus the action."""

    model_config = ConfigDict(extra="forbid")

    persisted: PersistedSession
    action: TurnRequest


class TurnResponseEnvelope(BaseModel):
    """Stateless turn response: the updated view plus the new persisted blob."""

    view: TurnResponse
    persisted: PersistedSession


class CastRequest(BaseModel):
    """Stateless cast detail request."""

    model_config = ConfigDict(extra="forbid")

    persisted: PersistedSession
    npc_id: str


class CastDetail(BaseModel):
    id: str
    name: str
    gender: str
    archetype: str
    mood: str
    location: str
    backstory: str
    familiarity: int
    relationship: ApiRelationship
    type_on_paper: dict[str, object | None]
    known_facts: list[ApiKnownFact]
    memories: list[ApiMemory]
    coupled_with: str | None
    eliminated: bool


class CouplesResponse(BaseModel):
    couples: list[CoupleSummary]
    singles: list[str]


class VersionResponse(BaseModel):
    schema_version: int
    api_version: str
    build: str
