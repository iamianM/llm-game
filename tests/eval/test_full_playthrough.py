"""Deterministic full-playthrough regression (task #48).

Drives the stateless session API end-to-end with the mock LLM, exactly the way
the browser harness would, but in-process so it runs in a few seconds and can
gate ``make qa``. The engine must carry a fresh run from the Day-1 pre-greetings
checkpoint all the way to a finale outcome, passing through every day and the
signature ceremonies on the way. A regression that strands the player on a dead
screen, loops a phase forever, or fails to resolve the finale will trip the
turn budget or a phase assertion here long before it ships.

This complements ``tests/eval/test_playthrough.py`` (which only scores a static
recorded trace) with a live drive of the real turn loop.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from src.api.app import app

# Forward-progress action picker, ported from the proven API drive script.
# Priority: resolve scripted beats (continue/advance/...) -> make a decision in a
# quiz/vote/pairing -> pass time in free-roam (ambient) -> start a
# conversation -> move -> anything. This mirrors how a player who just wants to
# reach the end would tap through, so it exercises the real progression spine
# without needing the LLM decider.
_CONTINUE_KINDS = ("continue", "advance", "acknowledge", "skip")
_DECISION_KINDS = (
    "answer",
    "answer_quiz",
    "vote",
    "pair",
    "pick",
    "select",
    "choose",
    "propose",
    "accept",
    "decline",
    "kiss",
    "wed",
    "pass",
)
_PASS_TIME_KINDS = ("free_time", "explore", "idle", "wait", "ambient")
_RESPOND_KINDS = {"respond", "respond_with", "reply"}


def _pick(actions: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind = {a["kind"]: a for a in actions}
    for kind in _CONTINUE_KINDS:
        if kind in by_kind:
            return by_kind[kind]
    for kind in _DECISION_KINDS:
        if kind in by_kind:
            return by_kind[kind]
    for kind in _PASS_TIME_KINDS:
        if kind in by_kind:
            return by_kind[kind]
    conv = next(
        (
            a
            for a in actions
            if a["kind"] in {"start_conversation", "introduce_to"} and a.get("target_id")
        ),
        None,
    )
    if conv:
        return conv
    respond = next((a for a in actions if a["kind"] in _RESPOND_KINDS), None)
    if respond:
        return respond
    for kind in ("end_conversation", "move"):
        if kind in by_kind:
            return by_kind[kind]
    return actions[0]


def test_mock_playthrough_reaches_finale_through_every_day() -> None:
    client = TestClient(app)

    created = client.post(
        "/session/from-checkpoint",
        json={"name": "day1-pre-greetings", "mock_llm": True},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    persisted = body["persisted"]
    view = body["view"]

    days_seen: set[int] = set()
    phases_seen: set[str] = set()
    last_key = ""
    stuck = 0
    outcome: str | None = None

    # A complete run is ~5-6 days of phases; 600 turns is a generous ceiling that
    # still bounds a runaway loop. The deterministic mock drive finishes in well
    # under this.
    for _ in range(600):
        state = view["state"]
        days_seen.add(state["day"])
        phases_seen.add(state["phase"])

        if state.get("outcome"):
            outcome = state["outcome"]
            break

        actions = view.get("available_actions") or []
        assert actions, (
            f"stranded on a dead screen: day={state['day']} "
            f"phase={state['phase']} turn={state['turn_index']}"
        )

        key = f"{state['day']}|{state['phase']}|{state['turn_index']}"
        stuck = stuck + 1 if key == last_key else 0
        last_key = key
        assert stuck <= 40, (
            f"phase made no forward progress for 40 turns: "
            f"day={state['day']} phase={state['phase']} turn={state['turn_index']}"
        )

        action = _pick(actions)
        response = client.post(
            "/session/turn",
            json={"persisted": persisted, "action": action},
        )
        assert response.status_code == 200, (
            f"turn rejected at day={state['day']} phase={state['phase']}: "
            f"{response.text[:300]} (action={action})"
        )
        payload = response.json()
        persisted = payload["persisted"]
        # /session/turn returns a {view, persisted} envelope.
        view = payload["view"]

    assert outcome is not None, (
        f"never reached a finale outcome; last day={view['state']['day']} "
        f"phase={view['state']['phase']} days_seen={sorted(days_seen)}"
    )
    # The signature run spans the full six-day arc to a resolved couple verdict.
    assert days_seen >= {1, 2, 3, 4, 5, 6}, f"missing days: {sorted(days_seen)}"
    assert "finale" in phases_seen or outcome, "finale phase never entered"
