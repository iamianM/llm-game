"""Stateless SSE endpoint tests."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.api.app import app


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
