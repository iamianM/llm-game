"""Blackfen Road HTTP API models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.blackfen.models import GameState, RunStatus
from src.blackfen.rng import SeededRng

PERSISTED_SCHEMA_VERSION = 1


class BlackfenPersistedSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persisted_schema_version: int = PERSISTED_SCHEMA_VERSION
    game_id: Literal["blackfen_road"] = "blackfen_road"
    session_id: str
    user_id: str | None = None
    seed: int
    rng_state: list[object]
    game_state: dict[str, object]
    mock_llm: bool = True


class NewBlackfenSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_id: Literal["fighter", "rogue", "mage"] = "fighter"
    player_name: str = "You"
    seed: int | None = None
    mock_llm: bool | None = None


class BlackfenTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)


class BlackfenTurnEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persisted: BlackfenPersistedSession
    action: BlackfenTurnRequest


class BlackfenLocationView(BaseModel):
    id: str
    name: str
    kind: str
    image: str
    description: str
    exits: list[str]
    npcs: list[str]


class BlackfenActorView(BaseModel):
    id: str
    name: str
    hp: int
    max_hp: int
    armor_class: int


class BlackfenNpcView(BaseModel):
    id: str
    name: str
    role: str
    image: str
    disposition: str


class BlackfenMonsterView(BaseModel):
    id: str
    name: str
    image: str
    hp: int


class BlackfenItemView(BaseModel):
    id: str
    name: str
    kind: str
    image: str
    description: str


class BlackfenTurnLogEntry(BaseModel):
    turn_index: int
    raw_text: str
    narration: str
    summary: str
    damage_to_player: int
    damage_to_companion: int
    damage_to_enemies: int
    items_gained: list[str]
    items_lost: list[str]


class BlackfenSessionState(BaseModel):
    session_id: str
    seed: int
    turn_index: int
    status: RunStatus
    state_hash: str
    current_location: BlackfenLocationView
    known_locations: list[BlackfenLocationView]
    player: BlackfenActorView
    companion: BlackfenActorView
    companion_stance: str
    npcs_here: list[BlackfenNpcView]
    monsters_here: list[BlackfenMonsterView]
    inventory: list[BlackfenItemView]
    quest_flags: list[str]
    journal: list[str]
    recent_turns: list[BlackfenTurnLogEntry]
    last_narration: str | None


class BlackfenSessionResponse(BaseModel):
    session_id: str
    state: BlackfenSessionState
    suggestions: list[str]


class NewBlackfenSessionEnvelope(BaseModel):
    view: BlackfenSessionResponse
    persisted: BlackfenPersistedSession


class BlackfenTurnResponse(BaseModel):
    state: BlackfenSessionState
    narration: str
    rolls: list[dict[str, object]]
    suggestions: list[str]


class BlackfenTurnResponseEnvelope(BaseModel):
    view: BlackfenTurnResponse
    persisted: BlackfenPersistedSession


def hydrate(persisted: BlackfenPersistedSession) -> tuple[GameState, SeededRng]:
    state = GameState.model_validate(persisted.game_state)
    rng = SeededRng.from_snapshot(persisted.seed, persisted.rng_state)
    return state, rng


def freeze(state: GameState, rng: SeededRng, *, session_id: str, mock_llm: bool) -> BlackfenPersistedSession:
    return BlackfenPersistedSession(
        session_id=session_id,
        seed=state.seed,
        rng_state=rng.snapshot(),
        game_state=state.model_dump(mode="json"),
        mock_llm=mock_llm,
    )
