"""Reusable turn-card blocks for review packet HTML."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_base import escape


def exchange_block(exchange: object) -> str:
    """Render one player/NPC exchange."""
    if not isinstance(exchange, dict):
        return ""
    return (
        "<div class='card'>"
        f"<p><b>You:</b> {escape(exchange.get('player_dialogue', ''))}</p>"
        f"<p><b>Islander:</b> {escape(exchange.get('npc_dialogue', ''))}</p>"
        f"<p class='meta'>Tone: {escape(exchange.get('npc_tone', ''))}; "
        f"mood after: {escape(exchange.get('npc_mood_after', ''))}</p>"
        "</div>"
    )


def event_block(event_narration: object) -> str:
    """Render event narration."""
    if not isinstance(event_narration, dict):
        return ""
    return (
        "<div class='card'>"
        f"<p><b>Event:</b> {escape(event_narration.get('prose', ''))}</p>"
        "</div>"
    )


def follow_up_block(menu: object) -> str:
    """Render generated follow-up wheel options."""
    if not isinstance(menu, dict):
        return ""
    grouped: dict[str, list[str]] = {}
    options = menu.get("options")
    if isinstance(options, list):
        for option in options:
            if not isinstance(option, dict):
                continue
            category = str(option.get("category", "other"))
            grouped.setdefault(category, []).append(
                f"<li>{escape(option.get('label', ''))} "
                f"<span class='meta'>({escape(option.get('intent_kind', ''))}, "
                f"{escape(option.get('risk', ''))})</span></li>"
            )
    option_groups = "".join(
        f"<h3>{escape(category.title())}</h3><ol>{''.join(items)}</ol>"
        for category, items in grouped.items()
    )
    exit_line = menu.get("npc_exit_line")
    exit_text = f"<p><b>Exit:</b> {escape(exit_line)}</p>" if exit_line else ""
    return (
        "<div class='card'>"
        "<p><b>Follow-up menu</b></p>"
        f"{option_groups}"
        f"{exit_text}"
        "</div>"
    )


def agent_commit_block(agent_commits: object) -> str:
    """Render a summary and details for agent commits."""
    if not isinstance(agent_commits, dict):
        return ""
    update = agent_commits.get("villa_update")
    if not isinstance(update, dict):
        return ""
    movements = update.get("npc_movements")
    starts = update.get("conversation_starts")
    continues = update.get("conversation_continues")
    ends = update.get("conversation_ends")
    interruptions = update.get("npc_interruptions")
    background = agent_commits.get("background_dialogues")
    batches = agent_commits.get("curator_batches")
    rows = [
        f"<li>Movements: {len(movements) if isinstance(movements, list) else 0}</li>",
        f"<li>Starts: {len(starts) if isinstance(starts, list) else 0}</li>",
        f"<li>Continues: {len(continues) if isinstance(continues, list) else 0}</li>",
        f"<li>Ends: {len(ends) if isinstance(ends, list) else 0}</li>",
        f"<li>Interruptions: {len(interruptions) if isinstance(interruptions, list) else 0}</li>",
        f"<li>Background dialogue commits: {len(background) if isinstance(background, list) else 0}</li>",
        f"<li>Curator batches: {len(batches) if isinstance(batches, list) else 0}</li>",
    ]
    details = _agent_commit_details(update, background)
    return (
        "<div class='card'>"
        "<p><b>Villa agent commits</b></p>"
        f"<ul>{''.join(rows)}</ul>"
        f"{details}"
        "</div>"
    )


def autopilot_block(agent_commits: object) -> str:
    """Render Player Autopilot rationale when present."""
    if not isinstance(agent_commits, dict):
        return ""
    decision = agent_commits.get("player_autopilot")
    if not isinstance(decision, dict):
        return ""
    return (
        "<div class='card autopilot'>"
        "<p><b>Autopilot rationale</b></p>"
        f"<p><i>{escape(decision.get('rationale', ''))}</i></p>"
        f"<p class='meta'>Confidence: {escape(decision.get('confidence', ''))}; "
        f"action index: {escape(decision.get('chosen_action_index', ''))}</p>"
        "</div>"
    )


def pull_attempt_block(pull_attempt: object) -> str:
    """Render a pull-for-chat result."""
    if not isinstance(pull_attempt, dict):
        return ""
    outcome = "success" if pull_attempt.get("success") else "miss"
    deflection = pull_attempt.get("deflection_line")
    deflection_html = (
        "" if not isinstance(deflection, str) or not deflection else f"<p>{escape(deflection)}</p>"
    )
    return (
        "<div class='card pull-attempt'>"
        "<p><b>Pull attempt</b></p>"
        f"<p>Target: {escape(str(pull_attempt.get('target_id', 'unknown')))}; "
        f"chance {escape(str(pull_attempt.get('chance', '')))}; "
        f"roll {escape(str(pull_attempt.get('roll', '')))}; "
        f"outcome {escape(outcome)}.</p>"
        f"{deflection_html}"
        "</div>"
    )


def villa_snapshot_block(snapshot: object) -> str:
    """Render a per-turn map snapshot."""
    if not isinstance(snapshot, dict):
        return ""
    rows = []
    for location, occupants in snapshot.items():
        if not isinstance(occupants, list):
            continue
        rows.append(
            f"<li>{escape(location)}: {escape(', '.join(str(item) for item in occupants) or '(empty)')}</li>"
        )
    if not rows:
        return ""
    return f"<div class='card'><p><b>Villa snapshot</b></p><ul>{''.join(rows)}</ul></div>"


def couple_status_block(record: dict[str, Any]) -> str:
    strength = record.get("couple_strength")
    hideaway = record.get("hideaway")
    rows = []
    if isinstance(strength, int):
        rows.append(f"<li>Player couple strength: {strength}</li>")
    if isinstance(hideaway, dict) and hideaway.get("used_on_day") is not None:
        rows.append(
            f"<li>Hideaway used day {escape(hideaway.get('used_on_day'))} "
            f"with {escape(hideaway.get('partner_id', 'unknown'))}</li>"
        )
    return "" if not rows else f"<div class='card hideaway'><p><b>Couple status</b></p><ul>{''.join(rows)}</ul></div>"


def casa_amor_block(record: dict[str, Any]) -> str:
    """Render Casa Amor state when present."""
    villa = record.get("villa")
    casa = record.get("casa_amor")
    if villa != "casa_amor" and not isinstance(casa, dict):
        return ""
    rows = [f"<li>Current villa: {escape(villa or 'main')}</li>"]
    if isinstance(casa, dict):
        rows.append(f"<li>Started day: {escape(casa.get('started_on_day', 'unknown'))}</li>")
        rows.append(f"<li>Return day: {escape(casa.get('return_day', 'unknown'))}</li>")
        rows.append(f"<li>Decision: {escape(casa.get('player_decision') or 'pending')}</li>")
        rows.append(f"<li>Partners swapped: {escape(casa.get('partners_swapped', False))}</li>")
    return f"<div class='card casa-amor'><p><b>Casa Amor</b></p><ul>{''.join(rows)}</ul></div>"


def interruption_block(record: dict[str, Any]) -> str:
    """Render NPC interruption commits and player response."""
    commits = record.get("agent_commits")
    if not isinstance(commits, dict):
        return ""
    update = commits.get("villa_update")
    if not isinstance(update, dict):
        return ""
    interruptions = update.get("npc_interruptions")
    if not isinstance(interruptions, list) or not interruptions:
        return ""
    action = record.get("action")
    response = ""
    if isinstance(action, dict) and action.get("intent_id") in {
        "accept_interruption",
        "defer_interruption",
        "ignore_interruption",
    }:
        response = f"<p><b>Player response:</b> {escape(action.get('intent_id'))}</p>"
    items = "".join(
        f"<li>{escape(item.get('interrupter_id', 'npc'))}: {escape(item.get('reason', ''))}, "
        f"{escape(item.get('urgency', ''))}</li>"
        for item in interruptions
        if isinstance(item, dict)
    )
    return (
        "<div class='card interruption'>"
        "<p><b>NPC interruption</b></p>"
        f"<ul>{items}</ul>{response}"
        "</div>"
    )


def memory_block(agent_commits: object) -> str:
    """Render memories formed during a turn."""
    if not isinstance(agent_commits, dict):
        return ""
    batches = agent_commits.get("curator_batches")
    if not isinstance(batches, list) or not batches:
        return ""
    rows = []
    for batch in batches:
        if not isinstance(batch, dict):
            continue
        memories = batch.get("memories")
        if not isinstance(memories, list):
            continue
        for memory in memories:
            if isinstance(memory, dict):
                rows.append(_memory_row(memory))
    if not rows:
        return ""
    return f"<div class='card memory'><p><b>Memories formed this turn</b></p><ul>{''.join(rows)}</ul></div>"


def delta_text(result: dict[str, Any]) -> str:
    """Render relationship deltas compactly."""
    deltas = ", ".join(
        f"{target}: {delta}"
        for target, delta in result.get("relationship_deltas", {}).items()
    )
    return deltas or "none"


def _agent_commit_details(update: dict[str, object], background: object) -> str:
    lines = _movement_lines(update) + _conversation_lines(update) + _background_lines(background)
    if not lines:
        return ""
    return f"<p><b>Details</b></p><ul>{''.join(f'<li>{line}</li>' for line in lines)}</ul>"


def _movement_lines(update: dict[str, object]) -> list[str]:
    lines: list[str] = []
    movements = update.get("npc_movements")
    if isinstance(movements, list):
        for item in movements:
            if isinstance(item, dict):
                lines.append(
                    f"{escape(str(item.get('npc_id', 'npc')))} moved to "
                    f"{escape(str(item.get('target_location', 'unknown')))} "
                    f"({escape(str(item.get('reason', '')))})."
                )
    return lines


def _conversation_lines(update: dict[str, object]) -> list[str]:
    lines: list[str] = []
    lines.extend(_conversation_start_lines(update.get("conversation_starts")))
    lines.extend(_conversation_continue_lines(update.get("conversation_continues")))
    lines.extend(_conversation_end_lines(update.get("conversation_ends")))
    lines.extend(_interruption_lines(update.get("npc_interruptions")))
    return lines


def _conversation_start_lines(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    lines: list[str] = []
    for item in items:
        if isinstance(item, dict):
            participants = item.get("participants")
            label = " & ".join(str(value) for value in participants) if isinstance(participants, list) else "NPCs"
            lines.append(
                f"{escape(label)} started at {escape(str(item.get('location', 'unknown')))}: "
                f"\"{escape(str(item.get('topic', '')))}\"."
            )
    return lines


def _conversation_continue_lines(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    lines: list[str] = []
    for item in items:
        if isinstance(item, dict):
            nudge = str(item.get("nudge", ""))
            suffix = f': "{escape(nudge)}"' if nudge else ""
            lines.append(f"{escape(str(item.get('conversation_id', 'conversation')))} continued{suffix}.")
    return lines


def _conversation_end_lines(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    lines: list[str] = []
    for item in items:
        if isinstance(item, dict):
            lines.append(
                f"{escape(str(item.get('conversation_id', 'conversation')))} ended: "
                f"{escape(str(item.get('reason', '')))}."
            )
    return lines


def _interruption_lines(items: object) -> list[str]:
    if not isinstance(items, list):
        return []
    lines: list[str] = []
    for item in items:
        if isinstance(item, dict):
            lines.append(
                f"{escape(str(item.get('interrupter_id', 'npc')))} interrupted: "
                f"{escape(str(item.get('reason', '')))} / {escape(str(item.get('urgency', '')))}."
            )
    return lines


def _background_lines(background: object) -> list[str]:
    if not isinstance(background, list):
        return []
    lines: list[str] = []
    for item in background:
        if isinstance(item, dict):
            lines.append(
                f"Background ({escape(str(item.get('tone', 'unknown')))}): "
                f"\"{escape(_short_text(str(item.get('speaker_a_line', ''))))}\""
            )
    return lines


def _memory_row(memory: dict[str, object]) -> str:
    tags = memory.get("tags")
    tag_text = ", ".join(str(tag) for tag in tags) if isinstance(tags, list) else ""
    return (
        "<li>"
        f"<b>{escape(memory.get('holder_id', 'holder'))}</b> about "
        f"{escape(memory.get('subject_id', 'subject'))}: "
        f"{escape(memory.get('content', ''))} "
        f"<span class='meta'>weight {escape(memory.get('emotional_weight', ''))}; "
        f"{escape(tag_text)}</span></li>"
    )


def _short_text(value: str, *, limit: int = 140) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."
