"""FastAPI SSE endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.app import app
from src.api.session import SESSIONS


def test_turn_stream_emits_state_options_and_end_events() -> None:
    SESSIONS.clear()
    client = TestClient(app)
    created = client.post(
        "/session/new",
        json={"archetype": "class_clown", "player_gender": "man", "seed": 42},
    ).json()
    session_id = created["session_id"]
    action = created["available_actions"][0]

    response = client.post(f"/session/{session_id}/turn/stream", json=action)

    assert response.status_code == 200
    body = response.text
    assert "event: turn_start" in body
    assert "event: state" in body
    assert "event: options" in body
    assert "event: turn_end" in body
