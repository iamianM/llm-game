from fastapi.testclient import TestClient

from src.api.app import app
from src.blackfen.models import GameState, Intent, IntentKind, MechanicalResult


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


def test_blackfen_live_mode_uses_live_agent_classes(monkeypatch) -> None:
    class FakeLiveParser:
        def parse(self, _state: GameState, text: str) -> Intent:
            return Intent(kind=IntentKind.INSPECT, raw_text=text, approach="fake_live")

    class FakeLiveNarrator:
        def narrate(self, _state: GameState, result: MechanicalResult) -> str:
            return f"live narration for {result.intent.approach}"

    monkeypatch.setattr("src.blackfen.api.routes.OpenAIIntentParser", FakeLiveParser)
    monkeypatch.setattr("src.blackfen.api.routes.OpenAINarrator", FakeLiveNarrator)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = TestClient(app)
    response = client.post(
        "/blackfen/session/new",
        json={"seed": 42, "player_name": "Mara", "class_id": "fighter", "mock_llm": False},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["persisted"]["mock_llm"] is False

    turn = client.post(
        "/blackfen/session/turn",
        json={"persisted": body["persisted"], "action": {"text": "do something strange"}},
    )

    assert turn.status_code == 200
    assert turn.json()["view"]["narration"] == "live narration for fake_live"


def test_blackfen_live_mode_requires_server_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(app)

    response = client.post(
        "/blackfen/session/new",
        json={"seed": 42, "player_name": "Mara", "class_id": "fighter", "mock_llm": False},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["error"]["code"] == "LLM_UNAVAILABLE"
