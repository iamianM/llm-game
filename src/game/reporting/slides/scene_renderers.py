"""Render slide scene bodies."""

from __future__ import annotations

from src.game.reporting.html_arrivals import arrival_roll_block
from src.game.reporting.html_base import escape
from src.game.reporting.html_blocks import (
    autopilot_block,
    delta_text,
    event_block,
    exchange_block,
    follow_up_block,
    interruption_block,
    memory_block,
    pull_attempt_block,
    time_block,
    villa_snapshot_block,
)
from src.game.reporting.html_events import challenge_block, group_date_block, producer_text_block
from src.game.reporting.html_gather import pending_gather_block
from src.game.reporting.html_math import math_block
from src.game.reporting.scenes import Scene
from src.game.reporting.stylish.background import background_dialogue_block, daily_recap_block


def render_scene(scene: Scene) -> str:
    """Render one review scene."""
    records = "".join(_record_block(record) for record in scene.records)
    state_panel = _state_panel(scene.records[-1])
    return (
        f"<article class='scene-card'><h2>{escape(scene.title)}</h2>"
        f"<p class='scene-meta'>{escape(scene.kind)} · turns {scene.turn_range[0]}-{scene.turn_range[1]}</p>"
        f"{records}<div class='hidden' data-state-panel>{state_panel}</div></article>"
    )


def _record_block(record: dict[str, object]) -> str:
    result = record.get("mechanical_result")
    if not isinstance(result, dict):
        return ""
    action = result.get("action")
    if not isinstance(action, dict):
        return ""
    outcome = "success" if result.get("success") else "miss"
    return (
        f"<section class='record-block' id='turn-{escape(record.get('turn'))}'>"
        f"<p><b>Turn {escape(record.get('turn'))}</b> · Day {escape(record.get('day'))} · "
        f"{escape(record.get('phase'))} · {escape(record.get('location'))}</p>"
        f"<p><b>Choice:</b> {escape(action.get('kind'))} {escape(action.get('target_id') or '')} "
        f"{escape(action.get('intent_id') or '')} <span class='{outcome}'>{outcome}</span></p>"
        f"{time_block(record)}{challenge_block(record.get('challenge'))}{producer_text_block(record.get('producer_text'))}"
        f"{pending_gather_block(record)}{group_date_block(record.get('group_date'))}"
        f"{autopilot_block(record.get('agent_commits'))}"
        f"<details><summary>Success math</summary>{math_block(result)}</details>"
        f"{pull_attempt_block(result.get('pull_attempt'))}{interruption_block(record)}"
        f"{arrival_roll_block(record)}<div class='dialogue'>{exchange_block(record.get('exchange'))}</div>"
        f"{event_block(record.get('event_narration'))}{follow_up_block(record.get('follow_up_menu'))}"
        f"{background_dialogue_block(record)}{memory_block(record.get('agent_commits'))}"
        f"<p><b>Deltas:</b> {escape(delta_text(result))}</p></section>"
    )


def _state_panel(record: dict[str, object]) -> str:
    occupants = _occupant_buttons(record)
    memories = _memory_summary(record)
    return (
        "<h3>Scene State</h3>"
        f"<div class='state-card'><b>Day</b><br>{escape(record.get('day'))} / {escape(record.get('phase'))}</div>"
        f"<div class='state-card'><b>Location</b><br>{escape(record.get('location'))}</div>"
        f"<div class='state-card'><b>Visible</b><br>{escape(record.get('visible_state') or 'No visible islanders.')}</div>"
        f"<div class='state-card'><b>Villa</b>{occupants}</div>"
        f"<div class='state-card'><b>Memories formed</b>{memories}</div>"
        f"{villa_snapshot_block(record.get('villa_snapshot'))}"
        f"{daily_recap_block(record.get('day'), [record])}"
    )


def _occupant_buttons(record: dict[str, object]) -> str:
    snapshot = record.get("villa_snapshot")
    if not isinstance(snapshot, dict):
        return "<p class='meta'>No villa map in trace.</p>"
    chunks: list[str] = []
    dialogs: list[str] = []
    turn = escape(record.get("turn"))
    for location, occupants in snapshot.items():
        if not isinstance(occupants, list):
            continue
        names = []
        for occupant in occupants:
            name = str(occupant)
            dialog_id = f"cast-{turn}-{_slug(location)}-{_slug(name)}"
            names.append(
                f"<button class='cast-button' data-open-dialog='{escape(dialog_id)}'>{escape(name)}</button>"
            )
            dialogs.append(_cast_dialog(dialog_id, name, str(location), record))
        joined = "".join(names) if names else "<p class='meta'>Empty</p>"
        chunks.append(f"<details><summary>{escape(location)}</summary>{joined}</details>")
    return "".join(chunks) + "".join(dialogs)


def _cast_dialog(dialog_id: str, name: str, location: str, record: dict[str, object]) -> str:
    return (
        f"<dialog id='{escape(dialog_id)}'><button class='dialog-close' data-close-dialog>Close</button>"
        f"<h3>{escape(name)}</h3><p><b>Location:</b> {escape(location)}</p>"
        f"<p><b>Visible status:</b> {escape(record.get('visible_state') or 'No direct visible status.')}</p>"
        f"<div>{_memory_summary(record)}</div></dialog>"
    )


def _memory_summary(record: dict[str, object]) -> str:
    commits = record.get("agent_commits")
    if not isinstance(commits, dict):
        return "<p class='meta'>None recorded.</p>"
    batches = commits.get("curator_batches")
    if not isinstance(batches, list):
        return "<p class='meta'>None recorded.</p>"
    items: list[str] = []
    for batch in batches:
        if not isinstance(batch, dict):
            continue
        memories = batch.get("memories")
        if not isinstance(memories, list):
            continue
        for memory in memories[:4]:
            if isinstance(memory, dict):
                holder = memory.get("holder_id", "unknown")
                subject = memory.get("subject_id", "unknown")
                content = memory.get("content", "")
                items.append(
                    f"<li><b>{escape(holder)}</b> about {escape(subject)}: {escape(content)}</li>"
                )
    return "<ul>" + "".join(items) + "</ul>" if items else "<p class='meta'>None recorded.</p>"


def _slug(value: object) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in str(value)).strip("-")
