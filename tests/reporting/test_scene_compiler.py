"""Tests for slide scene compilation."""

from __future__ import annotations

from src.game.reporting.scenes import compile_scenes, scene_kind
from src.game.reporting.slides.session import slide_session_page


def test_scene_kind_detects_conversation() -> None:
    record = _record(1, "start_conversation")

    assert scene_kind(record) == "conversation"


def test_compile_scenes_groups_adjacent_conversation_turns() -> None:
    scenes = compile_scenes(
        [
            _record(1, "start_conversation"),
            _record(2, "respond_with"),
            _record(3, "advance_phase"),
        ]
    )

    assert [scene.kind for scene in scenes] == ["conversation", "turn"]
    assert scenes[0].turn_range == (1, 2)


def test_slide_session_page_contains_deck_controls() -> None:
    html = slide_session_page("Test Session", [_record(1, "advance_phase")])

    assert "data-next" in html
    assert "data-scene-target" in html
    assert "side-panel" in html


def test_slide_session_page_contains_state_popouts() -> None:
    html = slide_session_page("Test Session", [_record(1, "advance_phase")])

    assert "<dialog" in html
    assert "data-open-dialog" in html
    assert "Chloe" in html


def _record(turn: int, action_kind: str) -> dict[str, object]:
    return {
        "turn": turn,
        "day": 1,
        "phase": "morning",
        "location": "pool",
        "visible_state": "Chloe is here.",
        "villa_snapshot": {"pool": ["you", "Chloe"]},
        "mechanical_result": {
            "action": {"kind": action_kind, "target_id": "chloe"},
            "success": True,
            "roll": 12,
            "success_chance": 80,
            "relationship_deltas": {},
        },
        "agent_commits": {},
        "output_hash": "abc",
    }
