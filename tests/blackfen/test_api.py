from fastapi.testclient import TestClient

from src.api.app import app


def test_blackfen_session_and_turn_use_prefixed_routes() -> None:
    client = TestClient(app)
    response = client.post(
        "/blackfen/session/new",
        json={"seed": 42, "player_name": "Mara", "class_id": "fighter", "mock_llm": True},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["view"]["state"]["current_location"]["id"] == "blackfen_village"
    turn = client.post(
        "/blackfen/session/turn",
        json={"persisted": body["persisted"], "action": {"text": "talk to Mara Vell"}},
    )
    assert turn.status_code == 200
    turned = turn.json()
    assert turned["view"]["state"]["state_hash"] == "304a68f874c316e7"
    assert "Mara Vell" in turned["view"]["narration"]
