"""Tests for stylish review packet rendering."""

from __future__ import annotations

from src.game.reporting.memory_web import memory_web_svg
from src.game.reporting.stylish.avatars import avatar_svg
from src.game.reporting.stylish.background import daily_recap_block
from src.game.reporting.stylish.couple_status import couple_status_panel
from src.game.reporting.stylish.perception_graph import perception_graph_svg
from src.game.reporting.stylish.session import stylish_session_page
from src.game.reporting.stylish.timeline import day_nav
from tests.reporting.test_html import _record


def test_stylish_session_html_renders_with_minimal_trace() -> None:
    html = stylish_session_page("Session", [_record()])

    assert "class='shell'" in html
    assert "Day 1" in html
    assert "data-scene-index" in html


def test_stylish_session_html_self_contained_no_external_refs() -> None:
    html = stylish_session_page("Session", [_record()])

    assert "http://" not in html
    assert "https://" not in html
    assert "document.querySelectorAll" in html


def test_avatar_svg_color_deterministic_from_id() -> None:
    assert avatar_svg("chloe", "Chloe") == avatar_svg("chloe", "Chloe")


def test_timeline_marks_challenge_day() -> None:
    record = _record() | {"challenge": {"kind": "quiz"}}

    assert "▲ Day 1" in day_nav([record])


def test_timeline_marks_pairing_day() -> None:
    record = _record() | {"ceremony_events": [{"kind": "pairing"}]}

    assert "◆ Day 1" in day_nav([record])


def test_timeline_marks_flush_of_hearts_day() -> None:
    record = _record() | {"ceremony_events": [{"kind": "flush_of_hearts_departure"}]}

    assert "★ Day 1" in day_nav([record])


def test_couple_status_panel_shows_all_active_couples() -> None:
    record = _record() | {
        "audience_snapshot": {
            "entries": [
                {"couple": ["player", "chloe"], "score": 80, "is_player_couple": True},
                {"couple": ["maya", "liam"], "score": 55, "is_player_couple": False},
            ]
        },
        "couple_strength": 75,
    }

    html = couple_status_panel([record])

    assert "player &amp; chloe" in html
    assert "maya &amp; liam" in html


def test_couple_status_panel_highlights_player_couple() -> None:
    record = _record() | {"audience_snapshot": {"entries": [{"couple": ["player", "chloe"], "score": 80, "is_player_couple": True}]}}

    assert "couple player" in couple_status_panel([record])


def test_perception_graph_renders_one_line_per_couple() -> None:
    record = _record() | {"audience_snapshot": {"day": 1, "entries": [{"couple": ["player", "chloe"], "score": 80}]}}

    assert "<polyline" in perception_graph_svg([record])


def test_memory_web_excludes_low_weight_memories() -> None:
    record = _record()
    record["agent_commits"]["curator_batches"][0]["memories"][0]["emotional_weight"] = 1

    assert "No high-weight memories" in memory_web_svg([record])


def test_memory_web_renders_edge_styles_by_source() -> None:
    record = _record()
    record["agent_commits"]["curator_batches"][0]["memories"][0]["source"] = "witnessed"

    assert "stroke-dasharray='6 4'" in memory_web_svg([record])


def test_final_outcome_block_rendered_when_state_outcome_set() -> None:
    html = stylish_session_page("Session", [_record()], preface="<p>Final outcome: won_as_couple</p>")

    assert "Final outcome" in html


def test_math_breakdown_collapsed_by_default() -> None:
    html = stylish_session_page("Session", [_record()])

    assert "Why this outcome?" in html
    assert "inline-detail" in html


def test_daily_recap_block_renders_both_projected_sections() -> None:
    record = _record() | {
        "daily_recaps": [
            {
                "day": 1,
                "resort_id": "main",
                "resort_label": "Sunset Bay",
                "items": [
                    {
                        "section": "your_day",
                        "speaker_label": "You",
                        "content": "You chose honesty.",
                        "emphasis": "strong",
                    },
                    {
                        "section": "while_busy",
                        "speaker_label": "Chloe",
                        "content": "Chloe heard a rumor.",
                        "emphasis": "standard",
                    },
                ],
            }
        ]
    }

    html = daily_recap_block(2, [record])

    assert "Your day" in html
    assert "While you were busy" in html
    assert "holder_id" not in html
