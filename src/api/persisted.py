"""Persisted session envelope.

The API is stateless: the client holds the full game state (in localStorage today,
in a Postgres-backed store once accounts exist) and submits it on every request.
This module defines the on-the-wire shape of that blob and the helpers that round-
trip a live ``GameState`` + ``SeededRng`` through JSON.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.game.state.models import GameState
from src.game.state.rng import SeededRng

PERSISTED_SCHEMA_VERSION = 1


class PersistedSession(BaseModel):
    """Self-contained session payload exchanged with the client.

    Versioned so future shape changes don't strand in-flight games. ``user_id`` is
    reserved for when accounts land — always ``None`` for anonymous play.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = PERSISTED_SCHEMA_VERSION
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str | None = None
    rng_state: list[Any]
    game_state: dict[str, Any]
    mock_llm: bool = True


def hydrate(persisted: PersistedSession) -> tuple[GameState, SeededRng]:
    """Reconstruct live engine objects from a persisted envelope."""
    state = GameState.model_validate(persisted.game_state)
    rng = SeededRng.from_snapshot(state.seed, persisted.rng_state)
    return state, rng


def freeze(
    state: GameState,
    rng: SeededRng,
    *,
    session_id: str,
    user_id: str | None,
    mock_llm: bool,
) -> PersistedSession:
    """Capture live engine objects into a persisted envelope."""
    return PersistedSession(
        schema_version=PERSISTED_SCHEMA_VERSION,
        session_id=session_id,
        user_id=user_id,
        rng_state=rng.snapshot(),
        game_state=state.model_dump(mode="json"),
        mock_llm=mock_llm,
    )
