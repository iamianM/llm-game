"""Compile recorded turn traces into review scenes."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

SceneKind = Literal[
    "conversation",
    "ceremony",
    "gather",
    "background",
    "movement",
    "ambient",
    "challenge",
    "day_boundary",
    "turn",
]


class Scene(BaseModel):
    """One reviewable scene in a recorded playthrough."""

    model_config = ConfigDict(extra="forbid")

    scene_id: str
    kind: SceneKind
    turn_range: tuple[int, int]
    title: str
    records: list[dict[str, Any]]


def compile_scenes(records: list[dict[str, Any]]) -> list[Scene]:
    """Group turn records into coherent review scenes."""
    scenes: list[Scene] = []
    pending: list[dict[str, Any]] = []
    pending_kind: SceneKind | None = None
    for record in records:
        kind = scene_kind(record)
        if pending and (kind != pending_kind or _must_break_scene(pending[-1], record)):
            scenes.append(_scene(len(scenes), pending_kind or "turn", pending))
            pending = []
        pending.append(record)
        pending_kind = kind
    if pending:
        scenes.append(_scene(len(scenes), pending_kind or "turn", pending))
    return scenes


def scene_kind(record: dict[str, Any]) -> SceneKind:
    """Classify a trace record for scene grouping."""
    if record.get("ceremony_events") or record.get("event_narration"):
        return "ceremony"
    action = record.get("mechanical_result", {}).get("action", {})
    kind = str(action.get("kind") or "")
    if kind in {"start_conversation", "respond_with", "end_conversation"}:
        return "conversation"
    if kind in {"introduce_to"}:
        return "conversation"
    if kind == "ambient":
        return "ambient"
    if kind == "join_gather" or record.get("pending_gather"):
        return "gather"
    if record.get("challenge") or kind == "challenge_response":
        return "challenge"
    if record.get("daily_recaps"):
        return "day_boundary"
    commits = record.get("agent_commits") or {}
    resort_update = commits.get("resort_update") or {}
    if commits.get("background_dialogues"):
        return "background"
    if resort_update.get("npc_movements"):
        return "movement"
    return "turn"


def _must_break_scene(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    previous_turn = int(previous.get("turn", 0))
    current_turn = int(current.get("turn", 0))
    if current_turn != previous_turn + 1:
        return True
    return previous.get("day") != current.get("day")


def _scene(index: int, kind: SceneKind, records: list[dict[str, Any]]) -> Scene:
    first = records[0]
    last = records[-1]
    first_turn = int(first.get("turn", 0))
    last_turn = int(last.get("turn", first_turn))
    day = first.get("day", "?")
    return Scene(
        scene_id=f"scene-{index + 1}",
        kind=kind,
        turn_range=(first_turn, last_turn),
        title=_title(kind, day, first_turn, last_turn, records),
        records=records,
    )


def _title(
    kind: SceneKind,
    day: object,
    first_turn: int,
    last_turn: int,
    records: list[dict[str, Any]],
) -> str:
    span = f"turn {first_turn}" if first_turn == last_turn else f"turns {first_turn}-{last_turn}"
    if kind == "conversation":
        target = _conversation_target(records)
        return f"Day {day}: conversation with {target} ({span})"
    if kind == "ceremony":
        return f"Day {day}: event or ceremony ({span})"
    if kind == "gather":
        return f"Day {day}: gather moment ({span})"
    if kind == "background":
        return f"Day {day}: background Sunset Bay life ({span})"
    if kind == "movement":
        return f"Day {day}: Sunset Bay movement ({span})"
    if kind == "ambient":
        return f"Day {day}: ambient Sunset Bay time ({span})"
    if kind == "challenge":
        return f"Day {day}: challenge ({span})"
    if kind == "day_boundary":
        return f"Day {day}: daily recap ({span})"
    return f"Day {day}: turn review ({span})"


def _conversation_target(records: list[dict[str, Any]]) -> str:
    for record in records:
        action = record.get("mechanical_result", {}).get("action", {})
        target = action.get("target_id")
        if target:
            return str(target).title()
    return "heartbreaker"
