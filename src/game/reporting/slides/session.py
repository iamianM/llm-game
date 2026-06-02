"""Slide-deck session report composition."""

from __future__ import annotations

import json
from typing import Any

from src.game.reporting.html_base import escape
from src.game.reporting.scenes import Scene, compile_scenes
from src.game.reporting.slides.cast import (
    collect_cast,
    display_name,
    player_partner_id,
    render_cast_grid,
    render_cast_popouts,
    render_couples_panel,
)
from src.game.reporting.slides.css import SLIDE_CSS
from src.game.reporting.slides.js import SLIDE_JS
from src.game.reporting.slides.scene_renderers import (
    SCENE_KIND_ICON,
    _ceremony_title,
    _challenge_title,
    phase_label,
    render_scene,
    scene_clock_range,
)

BOOKMARK_GROUPS = [
    ("event", "Events"),
    ("highlight", "Highlights"),
    ("anomaly", "Anomalies"),
    ("error", "Errors"),
    ("note", "Notes"),
    ("regression", "Regressions"),
    ("smell", "Smells"),
]


def slide_session_page(
    title: str,
    records: list[dict[str, Any]],
    preface: str = "",
    reviewer_notes: list[dict[str, object]] | None = None,
    final_state: dict[str, Any] | None = None,
) -> str:
    """Render a self-contained slide deck for a recorded session."""
    scenes = compile_scenes(records)
    days = _group_scenes_by_day(scenes)
    cast = collect_cast(records, final_state)
    partner_id = player_partner_id(final_state)
    day_pills = _render_day_pills(days)
    scene_nav_html = _render_scene_nav(days)
    scenes_html = "".join(_render_scene_wrapper(scene, index) for index, scene in enumerate(scenes))
    cast_popouts = render_cast_popouts(cast, records)
    bookmarks_html = _render_bookmarks(records, scenes, reviewer_notes or [])
    scene_meta = _scene_metadata(scenes)
    run_header = _render_run_header(title, final_state, preface)
    about_dialog = _render_about_dialog(preface)
    couples_html = render_couples_panel(final_state, cast)
    body = (
        "<div class='shell'>"
        f"{run_header}"
        f"<div class='day-strip'>{day_pills}</div>"
        "<div class='layout'>"
        f"<aside class='scene-nav'><h4>Timeline</h4>{scene_nav_html}</aside>"
        f"<main class='stage'>{scenes_html}</main>"
        "<aside class='right-rail'>"
        "<section><h4>Where everyone is</h4><div id='resort-map-host'></div></section>"
        f"<section><h4>Couples</h4>{couples_html}</section>"
        f"<section><h4>Cast</h4>{render_cast_grid(cast, partner_id)}</section>"
        f"<section><h4>Bookmarks</h4>{bookmarks_html}</section>"
        "</aside>"
        "</div></div>"
        f"{cast_popouts}{about_dialog}"
        f"<script type='application/json' id='scene-meta'>{escape(json.dumps(scene_meta))}</script>"
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{escape(title)}</title><style>{SLIDE_CSS}</style></head>"
        f"<body>{body}<script>{SLIDE_JS}</script></body></html>"
    )


def _render_run_header(title: str, final_state: dict[str, Any] | None, preface: str) -> str:
    badges: list[str] = []
    if isinstance(final_state, dict):
        player = final_state.get("player") if isinstance(final_state.get("player"), dict) else None
        if isinstance(player, dict):
            archetype = str(player.get("archetype") or "").strip()
            persona = str(player.get("persona") or "").strip()
            if archetype:
                badges.append(f"<span class='badge'>{escape(archetype.title())}</span>")
            if persona:
                badges.append(f"<span class='badge'>persona · {escape(persona)}</span>")
        outcome = str(final_state.get("outcome") or "").strip()
        if outcome:
            partner_label = ""
            partner_id = player_partner_id(final_state)
            if partner_id:
                heartbreakers = final_state.get("heartbreakers") or []
                if isinstance(heartbreakers, list):
                    for isl in heartbreakers:
                        if isinstance(isl, dict) and isl.get("id") == partner_id:
                            partner_label = f" with {escape(str(isl.get('name') or display_name(partner_id)))}"
                            break
            label = outcome.replace("_", " ").title()
            badges.append(
                f"<span class='badge outcome-{escape(outcome)}'>{escape(label)}{partner_label}</span>"
            )
        day = final_state.get("day")
        if day is not None:
            badges.append(f"<span class='badge'>Day {escape(day)}</span>")
    meta = "".join(badges)
    about_btn = (
        "<button class='about-btn' data-open-dialog='about-run' title='Run details'>About this run</button>"
        if preface else ""
    )
    return (
        f"<header class='run-header'>"
        f"<div class='run-title'><h1>{escape(title)}</h1><div class='run-meta'>{meta}{about_btn}</div></div>"
        f"</header>"
    )


def _render_about_dialog(preface: str) -> str:
    if not preface:
        return ""
    return (
        "<dialog id='about-run'>"
        "<div class='dialog-head'><h3>About this run</h3>"
        "<button class='dialog-close' data-close-dialog aria-label='Close'>×</button></div>"
        f"<div class='dialog-body'>{preface}</div></dialog>"
    )


def _group_scenes_by_day(scenes: list[Scene]) -> dict[str, list[tuple[int, Scene]]]:
    grouped: dict[str, list[tuple[int, Scene]]] = {}
    for idx, scene in enumerate(scenes):
        day = "?"
        if scene.records:
            day_val = scene.records[0].get("day")
            if day_val is not None:
                day = str(day_val)
        grouped.setdefault(day, []).append((idx, scene))
    return grouped


def _render_day_pills(days: dict[str, list[tuple[int, Scene]]]) -> str:
    pills: list[str] = []
    for day, scene_pairs in days.items():
        count = len(scene_pairs)
        first_index = scene_pairs[0][0]
        pills.append(
            f"<button class='day-pill' data-day='{escape(day)}' data-first-scene='{first_index}'>"
            f"Day {escape(day)}<span class='day-count'>· {count}</span></button>"
        )
    return "".join(pills)


def _render_scene_nav(days: dict[str, list[tuple[int, Scene]]]) -> str:
    sections: list[str] = []
    for day, scene_pairs in days.items():
        items: list[str] = []
        for idx, scene in scene_pairs:
            icon = SCENE_KIND_ICON.get(scene.kind, "•")
            label = _short_scene_label(scene)
            time_label = _scene_time_label(scene)
            items.append(
                f"<li><button class='scene-btn' data-scene-index='{idx}'>"
                f"<span class='icon'>{icon}</span>"
                f"<span class='label'>{escape(label)}</span>"
                f"<span class='time'>{escape(time_label)}</span></button></li>"
            )
        sections.append(
            f"<div class='day-section'>"
            f"<div class='day-section-head'>Day {escape(day)}"
            f"<span class='count'>{len(scene_pairs)} scenes</span></div>"
            f"<ul class='scene-list' data-day='{escape(day)}'>{''.join(items)}</ul>"
            f"</div>"
        )
    return "".join(sections)


def _short_scene_label(scene: Scene) -> str:
    if scene.kind == "conversation":
        for record in scene.records:
            action = record.get("mechanical_result", {}).get("action", {})
            target = action.get("target_id")
            if target:
                return f"Chat · {display_name(str(target))}"
        return "Conversation"
    if scene.kind == "ceremony":
        day = scene.records[0].get("day") if scene.records else None
        for record in scene.records:
            events = record.get("ceremony_events")
            if isinstance(events, list) and events:
                ev = events[0]
                if isinstance(ev, dict):
                    kind = str(ev.get("kind") or "")
                    if kind:
                        return _ceremony_title(kind, day)
        return "Ceremony"
    if scene.kind == "challenge":
        for record in scene.records:
            chal = record.get("challenge")
            if isinstance(chal, dict):
                kind = str(chal.get("kind") or "")
                if kind:
                    return _challenge_title(kind)
        return "Challenge"
    if scene.kind == "gather":
        return "Gather"
    if scene.kind == "background":
        return "Background"
    if scene.kind == "movement":
        return "Movement"
    if scene.kind == "day_boundary":
        return "Day wraps"
    return "Moment"


def _scene_time_label(scene: Scene) -> str:
    """Real clock range for the scene nav, derived from engine phase_clock data.

    Falls back to the phase label when the trace predates phase_clock tracking.
    """
    if not scene.records:
        return ""
    clock = scene_clock_range(scene.records)
    if clock:
        return clock
    phase = str(scene.records[0].get("phase") or "")
    return phase_label(phase)


def _render_scene_wrapper(scene: Scene, index: int) -> str:
    day_value = scene.records[0].get("day", "?") if scene.records else "?"
    return (
        f"<section class='scene' data-scene-index='{index}' data-day='{escape(day_value)}'>"
        f"{render_scene(scene)}</section>"
    )


def _render_bookmarks(
    records: list[dict[str, Any]],
    scenes: list[Scene],
    reviewer_notes: list[dict[str, object]],
) -> str:
    turn_to_scene: dict[int, int] = {}
    for index, scene in enumerate(scenes):
        for turn in range(scene.turn_range[0], scene.turn_range[1] + 1):
            turn_to_scene[turn] = index
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        raw = record.get("bookmarks")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    cat = str(item.get("category") or "note")
                    grouped.setdefault(cat, []).append(item)
    for note in reviewer_notes:
        cat = str(note.get("category") or "note")
        grouped.setdefault(cat, []).append(note)
    blocks: list[str] = []
    for cat_key, cat_label in BOOKMARK_GROUPS:
        items = grouped.get(cat_key, [])
        if not items:
            continue
        item_html: list[str] = []
        for bm in items:
            turn = bm.get("turn")
            if not isinstance(turn, int):
                continue
            scene_idx = turn_to_scene.get(turn)
            if scene_idx is None:
                continue
            title = str(bm.get("title") or bm.get("kind") or "Bookmark")
            note = str(bm.get("note") or "")
            item_html.append(
                f"<button class='bm-item bm-{escape(cat_key)}' "
                f"data-scene-index='{scene_idx}' title='{escape(note)}'>"
                f"<span class='bm-dot'></span>"
                f"<span class='bm-title'>{escape(title)}</span></button>"
            )
        if item_html:
            blocks.append(
                f"<details class='bm-group' open><summary>{escape(cat_label)} · {len(item_html)}</summary>"
                f"<div class='bookmarks-list'>{''.join(item_html)}</div></details>"
            )
    if not blocks:
        return "<p class='muted small'>No bookmarks recorded.</p>"
    return "".join(blocks)


def _scene_metadata(scenes: list[Scene]) -> list[dict[str, Any]]:
    meta: list[dict[str, Any]] = []
    for index, scene in enumerate(scenes):
        first = scene.records[0] if scene.records else {}
        snapshot = first.get("resort_snapshot") if isinstance(first.get("resort_snapshot"), dict) else None
        meta.append({
            "index": index,
            "day": str(first.get("day", "?")),
            "phase": str(first.get("phase", "")),
            "kind": scene.kind,
            "resort_snapshot": snapshot or {},
        })
    return meta
