"""Tests for slide scene compilation."""

from __future__ import annotations

from src.game.reporting.scenes import compile_scenes, scene_kind
from src.game.reporting.slides.scene_inline import _intent_label, _is_player_batch
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

    assert "data-scene-index" in html
    assert "scene-nav" in html
    assert "right-rail" in html
    assert "day-pill" in html


def test_slide_session_page_contains_state_popouts() -> None:
    html = slide_session_page("Test Session", [_record(1, "advance_phase")])

    assert "<dialog" in html
    assert "data-open-dialog" in html
    assert "Chloe" in html


def test_slide_session_page_renders_auto_and_reviewer_bookmarks() -> None:
    record = _record(1, "advance_phase")
    record["bookmarks"] = [
        {"turn": 1, "kind": "auto_advance", "category": "event", "title": "Time expired"}
    ]
    html = slide_session_page(
        "Test Session",
        [record],
        reviewer_notes=[
            {"turn": 1, "kind": "review_note", "category": "note", "title": "Review this"}
        ],
    )

    assert "Time expired" in html
    assert "Review this" in html


def test_intent_label_hides_memory_suffix() -> None:
    assert _intent_label("share_gossip:mem_abc123") == "Share gossip"


def test_memory_batch_kind_drives_player_filter() -> None:
    player_batch = {"kind": "player", "memories": []}
    background_batch = {"kind": "background", "memories": [{"holder_id": "player"}]}

    assert _is_player_batch(player_batch)
    assert not _is_player_batch(background_batch)


def _record(turn: int, action_kind: str) -> dict[str, object]:
    return {
        "turn": turn,
        "day": 1,
        "phase": "morning",
        "location": "pool",
        "visible_state": "Chloe is here.",
        "resort_snapshot": {"pool": ["you", "Chloe"]},
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
