"""FastAPI session endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.app import app
from src.api.session import SESSIONS


def test_create_get_and_delete_session() -> None:
    SESSIONS.clear()
    client = TestClient(app)

    created = client.post(
        "/session/new",
        json={"archetype": "heartthrob", "player_gender": "man", "seed": 42},
    )

    assert created.status_code == 201
    payload = created.json()
    session_id = payload["session_id"]
    assert payload["state"]["villa_label"] == "Sunset Bay"
    assert payload["available_actions"]

    fetched = client.get(f"/session/{session_id}")
    assert fetched.status_code == 200
    assert fetched.json()["session_id"] == session_id

    deleted = client.delete(f"/session/{session_id}")
    assert deleted.status_code == 204
    assert client.get(f"/session/{session_id}").status_code == 404


def test_get_missing_session_returns_404() -> None:
    SESSIONS.clear()
    client = TestClient(app)

    response = client.get("/session/missing")

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "SESSION_NOT_FOUND"
