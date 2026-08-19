"""Render slide scene bodies as polished, kind-specific layouts."""

from __future__ import annotations

from src.game.reporting.html_base import escape
from src.game.reporting.scenes import Scene
from src.game.reporting.slides.cast import display_name
from src.game.reporting.slides.scene_dialogue import _conversation_body
from src.game.reporting.slides.scene_event_bodies import (
    _background_body,
    _ceremony_body,
    _challenge_body,
    _day_boundary_body,
    _gather_body,
    _movement_body,
    _turn_body,
)
from src.game.reporting.slides.scene_time import phase_label, scene_clock_range
from src.game.reporting.slides.scene_titles import (
    _ceremony_title,
    _challenge_title,
    _conversation_target,
)

SCENE_KIND_ICON = {
    "conversation": "💬",
    "ceremony": "✨",
    "challenge": "🎯",
    "gather": "🔔",
    "background": "👥",
    "movement": "🚶",
    "ambient": "☀",
    "day_boundary": "🌅",
    "turn": "•",
}

SCENE_KIND_LABEL = {
    "conversation": "Conversation",
    "ceremony": "Ceremony",
    "challenge": "Challenge",
    "gather": "Gather",
    "background": "Background",
    "movement": "Movement",
    "ambient": "Sunset Bay time",
    "day_boundary": "Day end",
    "turn": "Moment",
}

def render_scene(scene: Scene) -> str:
    """Render one review scene with kind-specific body."""
    first = scene.records[0]
    last = scene.records[-1]
    day = first.get("day", "?")
    phase = first.get("phase", "")
    location = first.get("location", "")
    icon = SCENE_KIND_ICON.get(scene.kind, "•")
    kind_label = SCENE_KIND_LABEL.get(scene.kind, scene.kind.title())
    first_turn = first.get("turn", "?")
    last_turn = last.get("turn", first_turn)
    turn_range = (
        f"T{escape(first_turn)}" if first_turn == last_turn
        else f"T{escape(first_turn)}–T{escape(last_turn)}"
    )
    clock_range = scene_clock_range(scene.records)
    clock_html = (
        f"<span class='clock-pill'>🕒 {escape(clock_range)}</span> · " if clock_range else ""
    )
    anchors = "".join(
        f"<span id='turn-{escape(record.get('turn', ''))}' class='turn-anchor'></span>"
        for record in scene.records
    )
    header = (
        f"{anchors}"
        f"<header class='scene-header'>"
        f"<div class='title-row'>"
        f"<span class='scene-kind-chip scene-kind-{escape(scene.kind)}'>{icon} {escape(kind_label)}</span>"
        f"<h2>{escape(_scene_title(scene))}</h2>"
        f"</div>"
        f"<p class='scene-meta'>"
        f"{clock_html}"
        f"<span class='turn-range'>{turn_range}</span>"
        f" · Day {escape(day)} · {escape(phase_label(str(phase)))}"
        f"{(' · ' + escape(display_name(str(location)))) if location else ''}</p>"
        f"</header>"
    )
    body = _scene_body(scene)
    return f"{header}{body}"


def _scene_title(scene: Scene) -> str:
    first = scene.records[0]
    day = first.get("day", "?")
    if scene.kind == "conversation":
        target = _conversation_target(scene.records)
        return f"Conversation with {display_name(target)}" if target else "Conversation"
    if scene.kind == "ceremony":
        for record in scene.records:
            events = record.get("ceremony_events")
            if isinstance(events, list) and events:
                ev = events[0]
                if isinstance(ev, dict):
                    kind = str(ev.get("kind") or "")
                    return _ceremony_title(kind, day)
        return "Ceremony"
    if scene.kind == "challenge":
        for record in scene.records:
            chal = record.get("challenge")
            if isinstance(chal, dict):
                kind = str(chal.get("kind") or "")
                return _challenge_title(kind)
        return "Challenge"
    if scene.kind == "gather":
        return "Everyone gathers"
    if scene.kind == "background":
        return "Around Sunset Bay"
    if scene.kind == "movement":
        return "Sunset Bay shifts"
    if scene.kind == "ambient":
        return "Sunset Bay time"
    if scene.kind == "day_boundary":
        return f"Day {first.get('day', '?')} wraps"
    return f"Turn {first.get('turn', '?')}"


def _scene_body(scene: Scene) -> str:
    if scene.kind == "conversation":
        return _conversation_body(scene)
    if scene.kind == "ceremony":
        return _ceremony_body(scene)
    if scene.kind == "challenge":
        return _challenge_body(scene)
    if scene.kind == "gather":
        return _gather_body(scene)
    if scene.kind == "background":
        return _background_body(scene)
    if scene.kind == "movement":
        return _movement_body(scene)
    if scene.kind == "ambient":
        return _turn_body(scene)
    if scene.kind == "day_boundary":
        return _day_boundary_body(scene)
    return _turn_body(scene)
