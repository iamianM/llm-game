"""FastAPI turn endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.app import app
from src.api.session import SESSIONS


def test_submit_valid_turn_updates_state() -> None:
    SESSIONS.clear()
    client = TestClient(app)
    session_id = _new_session(client)
    first = client.get(f"/session/{session_id}").json()["available_actions"][0]

    response = client.post(f"/session/{session_id}/turn", json=first)

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"]["turn_index"] == 1
    assert payload["available_actions"]
    assert payload["state_hash"]


def test_submit_invalid_turn_returns_400() -> None:
    SESSIONS.clear()
    client = TestClient(app)
    session_id = _new_session(client)

    response = client.post(f"/session/{session_id}/turn", json={"kind": "hideaway"})

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "INVALID_ACTION"


def _new_session(client: TestClient) -> str:
    response = client.post(
        "/session/new",
        json={"archetype": "loyal_friend", "player_gender": "man", "seed": 42},
    )
    assert response.status_code == 201
    return str(response.json()["session_id"])
