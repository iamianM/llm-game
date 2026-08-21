"""Stateless turn endpoint tests."""

from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from src.api import app as api_app
from src.game.agents.runtime import AgentValidationError
from src.game.agents.turn_agents import mock_turn_agents

app = api_app.app


def test_submit_valid_turn_updates_state_and_returns_new_persisted() -> None:
    client = TestClient(app)
    created = _new_session(client)
    first_action = created["view"]["available_actions"][0]

    response = client.post(
        "/session/turn",
        json={"persisted": created["persisted"], "action": first_action},
    )

    assert response.status_code == 200
    payload = response.json()
    view = payload["view"]
    assert view["state"]["turn_index"] == 1
    assert view["available_actions"]
    assert view["state_hash"]
    new_persisted = payload["persisted"]
    assert new_persisted["session_id"] == created["persisted"]["session_id"]
    assert new_persisted["game_state"]["turn_index"] == 1
    # rng_state round-trips structurally; engine may or may not advance the parent on a given turn
    assert isinstance(new_persisted["rng_state"], list)
    assert new_persisted["rng_state"][0] == created["persisted"]["rng_state"][0]


def test_submit_invalid_turn_returns_400() -> None:
    client = TestClient(app)
    created = _new_session(client)

    response = client.post(
        "/session/turn",
        json={"persisted": created["persisted"], "action": {"kind": "private_suite"}},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "INVALID_ACTION"


def test_two_consecutive_turns_advance_state() -> None:
    """A second turn submitted with the persisted blob from the first must compose."""
    client = TestClient(app)
    created = _new_session(client)
    first_action = created["view"]["available_actions"][0]

    first = client.post(
        "/session/turn",
        json={"persisted": created["persisted"], "action": first_action},
    ).json()
    second_action = first["view"]["available_actions"][0]

    second = client.post(
        "/session/turn",
        json={"persisted": first["persisted"], "action": second_action},
    )

    assert second.status_code == 200
    payload = second.json()
    assert payload["view"]["state"]["turn_index"] == 2
    assert payload["persisted"]["game_state"]["turn_index"] == 2


def test_story_engine_failure_returns_structured_502(monkeypatch) -> None:
    client = TestClient(app)
    created = _new_session(client)

    def boom(*_args, **_kwargs):
        raise AgentValidationError("voice contract failed")

    agents = replace(mock_turn_agents(), heartbreaker_voice=boom)
    monkeypatch.setattr(api_app, "_agents_for", lambda _mock_llm: agents)

    response = client.post(
        "/session/turn",
        json={
            "persisted": created["persisted"],
            "action": created["view"]["available_actions"][0],
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"]["error"]["code"] == "STORY_ENGINE_ERROR"


def _new_session(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/session/new",
        json={"archetype": "loyal_friend", "player_gender": "man", "seed": 42},
    )
    assert response.status_code == 201
    return response.json()
