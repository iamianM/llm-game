"""Stateless session endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.app import app


def test_new_session_returns_view_and_persisted_envelope() -> None:
    client = TestClient(app)

    created = client.post(
        "/session/new",
        json={"archetype": "heartthrob", "player_gender": "man", "seed": 42, "mock_llm": True},
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["view"]["session_id"]
    assert payload["view"]["state"]["villa_label"] == "Sunset Bay"
    assert payload["view"]["available_actions"]
    persisted = payload["persisted"]
    assert persisted["session_id"] == payload["view"]["session_id"]
    assert persisted["schema_version"] == 1
    assert persisted["user_id"] is None
    assert persisted["mock_llm"] is True
    assert persisted["game_state"]["seed"] == 42
    assert isinstance(persisted["rng_state"], list)


def test_view_session_rehydrates_persisted_envelope() -> None:
    client = TestClient(app)

    created = client.post(
        "/session/new",
        json={"archetype": "heartthrob", "player_gender": "man", "seed": 42, "mock_llm": True},
    ).json()

    rehydrated = client.post("/session/view", json=created["persisted"])

    assert rehydrated.status_code == 200
    body = rehydrated.json()
    assert body["session_id"] == created["view"]["session_id"]
    assert body["state"]["seed"] == 42
    assert body["available_actions"]


def test_tailscale_dev_origin_is_allowed() -> None:
    client = TestClient(app)

    response = client.options(
        "/healthz",
        headers={
            "Origin": "http://100.119.27.119:3001",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://100.119.27.119:3001"
