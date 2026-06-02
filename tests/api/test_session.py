"""Stateless session endpoint tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.checkpoints import list_checkpoints


def test_new_session_returns_view_and_persisted_envelope() -> None:
    client = TestClient(app)

    created = client.post(
        "/session/new",
        json={"archetype": "heartthrob", "player_gender": "man", "seed": 42, "mock_llm": True},
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["view"]["session_id"]
    assert payload["view"]["state"]["resort_label"] == "Sunset Bay"
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


@pytest.mark.parametrize("name", [ck.name for ck in list_checkpoints()])
def test_every_checkpoint_loads_into_a_playable_state(name: str) -> None:
    """No main-menu checkpoint may load onto a dead (zero-action) screen.

    Some endgame checkpoints were baked on a transient pre-event TEXT boundary
    that carries no available actions. The load path must settle such a state
    forward to the next playable beat so the picker never strands the player.
    """
    client = TestClient(app)

    created = client.post(
        "/session/from-checkpoint",
        json={"name": name, "mock_llm": True},
    )

    assert created.status_code == 201, created.text
    view = created.json()["view"]
    # A terminal end-state (e.g. the final reveal) legitimately has no actions;
    # the UI shows the outcome screen. Every *non-terminal* checkpoint, though,
    # must offer at least one action or the player is stranded.
    terminal = view["state"]["outcome"] is not None
    assert terminal or view["available_actions"], (
        f"checkpoint {name!r} loaded non-terminal with no available actions"
    )


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
