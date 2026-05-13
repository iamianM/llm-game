"""Slide-deck session report composition."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_base import escape
from src.game.reporting.scenes import Scene, compile_scenes
from src.game.reporting.slides.css import SLIDE_CSS
from src.game.reporting.slides.js import SLIDE_JS
from src.game.reporting.slides.scene_renderers import render_scene


def slide_session_page(
    title: str,
    records: list[dict[str, Any]],
    preface: str = "",
    reviewer_notes: list[dict[str, object]] | None = None,
) -> str:
    """Render a self-contained slide deck for a recorded session."""
    scenes = compile_scenes(records)
    timeline = "".join(
        f"<button data-scene-target='{index}' title='{escape(scene.title)}'>{index + 1}</button>"
        for index, scene in enumerate(scenes)
    )
    slides = "".join(
        f"<section class='slide' data-scene='{escape(scene.scene_id)}'>{render_scene(scene)}</section>"
        for scene in scenes
    )
    bookmarks = _bookmark_strip(records, scenes, reviewer_notes or [])
    body = (
        "<div class='review-shell'>"
        "<header class='topbar'>"
        f"<h1>{escape(title)}</h1><div class='timeline'>{timeline}</div>"
        f"<div class='bookmark-strip'>{bookmarks}</div></header>"
        "<div class='deck-layout'>"
        f"<main class='slides'>{preface}{slides}<div class='nav'><button data-prev>Previous</button><button data-next>Next</button></div></main>"
        "<aside class='side-panel'></aside>"
        "</div></div>"
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{escape(title)}</title><style>{SLIDE_CSS}</style></head>"
        f"<body>{body}<script>{SLIDE_JS}</script></body></html>"
    )


def _bookmark_strip(
    records: list[dict[str, Any]],
    scenes: list[Scene],
    reviewer_notes: list[dict[str, object]],
) -> str:
    turn_to_scene: dict[int, int] = {}
    for index, scene in enumerate(scenes):
        for turn in range(scene.turn_range[0], scene.turn_range[1] + 1):
            turn_to_scene[turn] = index
    bookmarks: list[dict[str, object]] = []
    for record in records:
        raw_bookmarks = record.get("bookmarks")
        if isinstance(raw_bookmarks, list):
            bookmarks.extend(item for item in raw_bookmarks if isinstance(item, dict))
    bookmarks.extend(reviewer_notes)
    chunks = []
    for bookmark in bookmarks:
        turn = bookmark.get("turn")
        if not isinstance(turn, int):
            continue
        scene_index = turn_to_scene.get(turn)
        if scene_index is None:
            continue
        category = str(bookmark.get("category") or "note")
        title = str(bookmark.get("title") or bookmark.get("kind") or "Bookmark")
        chunks.append(
            f"<button class='bookmark-{escape(category)}' data-scene-target='{scene_index}' "
            f"title='{escape(bookmark.get('note') or '')}'>{escape(title)}</button>"
        )
    return "".join(chunks)
