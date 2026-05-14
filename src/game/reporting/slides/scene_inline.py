"""Inline detail helpers for slide scene rendering."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_base import escape
from src.game.reporting.slides.cast import display_name
from src.game.reporting.slides.scene_time import turn_end_clock


def _turn_pill(record: dict[str, Any]) -> str:
    """Render a small pill with turn number + end-of-turn clock derived from engine data."""
    turn = record.get("turn")
    if turn is None:
        return ""
    clock = turn_end_clock(record)
    cost = record.get("time_cost") or 0
    cost_html = (
        f"<span class='cost'>+{escape(cost)}m</span>"
        if isinstance(cost, (int, float)) and cost > 0 else ""
    )
    clock_html = f"<span class='clock'>{escape(clock)}</span>" if clock else ""
    return f"<span class='turn-pill'>T{escape(turn)}{clock_html}{cost_html}</span>"


def _intent_label(intent_id: str) -> str:
    if not intent_id:
        return ""
    intent_id = intent_id.split(":", 1)[0]
    parts = intent_id.split("_")
    prefixes = {
        "friendly",
        "flirty",
        "deep",
        "banter",
        "supportive",
        "bromance",
        "gossip",
    }
    if len(parts) >= 2 and parts[0] in prefixes:
        return " ".join(parts[1:]).replace(":", " ").capitalize()
    return intent_id.replace("_", " ").replace(":", " ").capitalize()


def _delta_chip(result: dict[str, Any]) -> str:
    deltas = result.get("relationship_deltas")
    if not isinstance(deltas, dict):
        return ""
    parts: list[str] = []
    for _target, delta in deltas.items():
        if not isinstance(delta, dict):
            continue
        for key, val in delta.items():
            if not isinstance(val, (int, float)) or val == 0:
                continue
            sign = "+" if val > 0 else ""
            parts.append(f"{escape(key)} {sign}{int(val)}")
    if not parts:
        return ""
    return f"<span class='outcome-pill delta'>{', '.join(parts)}</span>"


def _audience_chip(result: dict[str, Any]) -> str:
    delta = result.get("audience_delta")
    if not isinstance(delta, (int, float)) or int(delta) == 0:
        return ""
    sign = "+" if int(delta) > 0 else ""
    reason = str(result.get("audience_reason") or "audience noticed")
    cls = "success" if int(delta) > 0 else "miss"
    return (
        f"<span class='outcome-pill {cls}'>Audience {sign}{int(delta)} · "
        f"{escape(reason)}</span>"
    )


def _render_menu_options(menu: dict[str, Any], chosen_intent: str) -> str:
    options = menu.get("options")
    if not isinstance(options, list):
        return ""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for opt in options:
        if not isinstance(opt, dict):
            continue
        cat = str(opt.get("category") or "other")
        grouped.setdefault(cat, []).append(opt)
    cat_order = [
        "friendly",
        "flirty",
        "deep",
        "banter",
        "bromance",
        "gossip_ring",
        "gossip",
        "supportive",
        "exit",
        "other",
    ]
    sections: list[str] = []
    for cat in cat_order:
        if cat not in grouped:
            continue
        opts_html: list[str] = []
        for opt in grouped[cat]:
            label = str(opt.get("label") or "")
            intent = str(opt.get("intent_kind") or opt.get("intent_id") or "")
            risk = str(opt.get("risk") or "")
            stat = str(opt.get("stat_used") or "")
            audience_hint = str(opt.get("audience_hint") or "")
            chosen = bool(chosen_intent and intent == chosen_intent)
            tag_parts = [risk]
            if stat:
                tag_parts.append(stat)
            if audience_hint:
                tag_parts.append(f"Audience {audience_hint}")
            tags = " · ".join(p for p in tag_parts if p)
            cls = "wheel-opt"
            if chosen:
                cls += " chosen"
            if cat == "exit":
                cls += " exit-opt"
            opts_html.append(
                f"<div class='{cls}'><span>{escape(label)}</span>"
                f"<span class='opt-tags'>{escape(tags)}</span></div>"
            )
        sections.append(
            f"<div class='wheel-cat-label'>{escape(cat.replace('_', ' ').title())}</div>"
            f"{''.join(opts_html)}"
        )
    if not sections:
        return ""
    return f"<div class='wheel-categories'>{''.join(sections)}</div>"


def _interruption_inset(record: dict[str, Any]) -> str:
    commits = record.get("agent_commits") or {}
    villa = commits.get("villa_update") if isinstance(commits, dict) else None
    if not isinstance(villa, dict):
        return ""
    interruptions = villa.get("npc_interruptions") or []
    if not interruptions:
        return ""
    parts: list[str] = []
    for it in interruptions:
        if not isinstance(it, dict):
            continue
        who = display_name(str(it.get("interrupter_id") or ""))
        reason = str(it.get("reason") or "").replace("_", " ")
        urgency = str(it.get("urgency") or "")
        parts.append(
            f"<div class='inset interruption-inset'>"
            f"<span class='inset-tag'>Interruption</span> "
            f"<b>{escape(who)}</b> cuts in "
            f"<span class='muted small'>· {escape(reason)} · {escape(urgency)}</span></div>"
        )
    return "".join(parts)


def _inline_mechanics(record: dict[str, Any]) -> str:
    result = record.get("mechanical_result") or {}
    parts: list[str] = []
    breakdown = result.get("chance_breakdown")
    if isinstance(breakdown, dict):
        roll = result.get("roll")
        chance = (
            result.get("final_chance")
            or result.get("success_chance")
            or breakdown.get("final_chance")
        )
        success = result.get("success")
        parts.append(
            f"<div class='mech-line'>"
            f"{_format_breakdown(breakdown)} "
            f"<span class='muted'>· rolled <code>{escape(roll)}</code> vs <code>{escape(chance)}</code> "
            f"→ <span class='{('success' if success else 'miss')}'>"
            f"{('success' if success else 'miss')}</span></span></div>"
        )
    pull = result.get("pull_attempt")
    if isinstance(pull, dict):
        pull_chance = pull.get("chance")
        pull_roll = pull.get("roll")
        pull_success = pull.get("success") is True
        parts.append(
            f"<div class='mech-line'>"
            f"<b>Pull attempt:</b> rolled <code>{escape(pull_roll)}</code> vs "
            f"<code>{escape(pull_chance)}</code> → "
            f"<span class='{('success' if pull_success else 'miss')}'>"
            f"{('success' if pull_success else 'rejected')}</span></div>"
        )
    return "".join(parts)


def _format_breakdown(b: dict[str, Any]) -> str:
    parts: list[str] = []
    base = b.get("base")
    if base is not None:
        parts.append(f"base {escape(base)}")
    stat_name = b.get("stat_name")
    stat_value = b.get("stat_value")
    stat_contrib = b.get("stat_contribution")
    if stat_name and stat_contrib is not None:
        parts.append(f"+ {escape(stat_contrib)} ({escape(stat_name)} {escape(stat_value)})")
    affection = b.get("affection_contribution")
    if affection is not None and affection != 0:
        parts.append(f"+ {escape(affection)} (affection)")
    risk = b.get("risk")
    risk_mod = b.get("risk_modifier")
    if risk and risk_mod is not None and risk_mod != 0:
        sign = "+" if int(risk_mod) > 0 else ""
        parts.append(f"{sign}{escape(risk_mod)} (risk: {escape(risk)})")
    mood_mod = b.get("mood_modifier")
    if mood_mod is not None and mood_mod != 0:
        sign = "+" if int(mood_mod) > 0 else ""
        parts.append(f"{sign}{escape(mood_mod)} (mood)")
    comp = b.get("compatibility_bonus")
    if comp is not None and comp != 0:
        sign = "+" if int(comp) > 0 else ""
        parts.append(f"{sign}{escape(comp)} (compatibility)")
    deal = b.get("dealbreaker_penalty")
    if deal is not None and deal != 0:
        parts.append(f"−{escape(deal)} (dealbreaker)")
    return " ".join(parts)


def _is_player_batch(batch: dict[str, Any]) -> bool:
    """A curator batch is player-relevant only when its typed kind says so.

    Witness-only batches (player observed an NPC↔NPC chat) don't count.
    """
    return batch.get("kind") == "player"


def _render_memory_batch(batch: dict[str, Any]) -> str:
    rows: list[str] = []
    summary = batch.get("summary")
    if isinstance(summary, str) and summary.strip():
        rows.append(f"<div class='mem-summary'><b>Summary:</b> {escape(summary)}</div>")
    memories = batch.get("memories") or []
    for m in memories:
        if not isinstance(m, dict):
            continue
        holder = display_name(str(m.get("holder_id") or ""))
        subject = display_name(str(m.get("subject_id") or ""))
        content = str(m.get("content") or "")
        weight = m.get("emotional_weight", "")
        source = str(m.get("source") or "direct")
        if not content:
            continue
        src_pill = (
            "<span class='mem-src witnessed'>witnessed</span>" if source == "witnessed" else ""
        )
        rows.append(
            f"<div class='mem-row'>"
            f"<div class='mem-meta'><b>{escape(holder)}</b> about {escape(subject)} "
            f"<span class='muted small'>· weight {escape(weight)}</span> {src_pill}</div>"
            f"<div class='mem-content'><i>{escape(content)}</i></div></div>"
        )
    return "".join(rows)


def _inline_memories(record: dict[str, Any]) -> str:
    """Player-relevant memory batches only."""
    commits = record.get("agent_commits") or {}
    if not isinstance(commits, dict):
        return ""
    batches = commits.get("curator_batches")
    if not isinstance(batches, list):
        return ""
    rows: list[str] = []
    for batch in batches:
        if not isinstance(batch, dict):
            continue
        if not _is_player_batch(batch):
            continue
        rows.append(_render_memory_batch(batch))
    return "".join(rows)


def _inline_background_activity(record: dict[str, Any]) -> str:
    """Non-player curator batches that happened in parallel (NPC↔NPC conversations).

    Rendered as a separate collapsible so they don't masquerade as player-chat memories.
    """
    commits = record.get("agent_commits") or {}
    if not isinstance(commits, dict):
        return ""
    batches = commits.get("curator_batches")
    if not isinstance(batches, list):
        return ""
    rows: list[str] = []
    for batch in batches:
        if not isinstance(batch, dict):
            continue
        if _is_player_batch(batch):
            continue
        participants = _batch_direct_participants(batch)
        header = ""
        if participants:
            names = " & ".join(display_name(p) for p in sorted(participants))
            header = f"<div class='bg-batch-head'>{escape(names)} elsewhere</div>"
        rows.append(f"<div class='bg-batch'>{header}{_render_memory_batch(batch)}</div>")
    return "".join(rows)


def _batch_direct_participants(batch: dict[str, Any]) -> set[str]:
    parts: set[str] = set()
    for m in batch.get("memories") or []:
        if not isinstance(m, dict):
            continue
        if str(m.get("source") or "direct") == "direct":
            holder = m.get("holder_id")
            if holder:
                parts.add(str(holder))
    return parts
