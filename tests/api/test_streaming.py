"""Stateless SSE endpoint tests."""

from __future__ import annotations

import json
from dataclasses import replace

from fastapi.testclient import TestClient

from src.api import app as api_app
from src.game.agents.runtime import AgentValidationError
from src.game.agents.turn_agents import mock_turn_agents

app = api_app.app


def test_turn_stream_emits_state_options_response_and_end_events() -> None:
    client = TestClient(app)
    created = client.post(
        "/session/new",
        json={"archetype": "class_clown", "player_gender": "man", "seed": 42},
    ).json()
    action = created["view"]["available_actions"][0]

    response = client.post(
        "/session/turn/stream",
        json={"persisted": created["persisted"], "action": action},
    )

    assert response.status_code == 200
    body = response.text
    assert "event: turn_start" in body
    assert "event: state" in body
    assert "event: options" in body
    assert "event: response" in body
    assert "event: turn_end" in body
    # the final response event must carry both the view and the new persisted blob
    response_frame = next(
        frame for frame in body.split("\n\n") if "event: response" in frame.splitlines()[:3]
    )
    data_line = next(line for line in response_frame.splitlines() if line.startswith("data:"))
    envelope = json.loads(data_line.removeprefix("data:").strip())
    assert "view" in envelope and "persisted" in envelope
    assert envelope["persisted"]["session_id"] == created["persisted"]["session_id"]
    assert envelope["persisted"]["game_state"]["turn_index"] == 1


def test_turn_stream_emits_structured_story_engine_error(monkeypatch) -> None:
    client = TestClient(app)
    created = client.post(
        "/session/new",
        json={"archetype": "class_clown", "player_gender": "man", "seed": 42},
    ).json()

    def boom(*_args, **_kwargs):
        raise AgentValidationError("voice contract failed")

    agents = replace(mock_turn_agents(), heartbreaker_voice=boom)
    monkeypatch.setattr(api_app, "_agents_for", lambda _mock_llm: agents)

    response = client.post(
        "/session/turn/stream",
        json={
            "persisted": created["persisted"],
            "action": created["view"]["available_actions"][0],
        },
    )

    error_frame = next(frame for frame in response.text.split("\n\n") if "event: error" in frame)
    data_line = next(line for line in error_frame.splitlines() if line.startswith("data:"))
    payload = json.loads(data_line.removeprefix("data:").strip())
    assert payload["status"] == 502
    assert payload["code"] == "STORY_ENGINE_ERROR"
