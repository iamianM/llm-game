"""Slide-deck session report composition."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_base import escape
from src.game.reporting.scenes import compile_scenes
from src.game.reporting.slides.css import SLIDE_CSS
from src.game.reporting.slides.js import SLIDE_JS
from src.game.reporting.slides.scene_renderers import render_scene


def slide_session_page(title: str, records: list[dict[str, Any]], preface: str = "") -> str:
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
    body = (
        "<div class='review-shell'>"
        "<header class='topbar'>"
        f"<h1>{escape(title)}</h1><div class='timeline'>{timeline}</div>"
        "<div class='bookmark-strip'></div></header>"
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
