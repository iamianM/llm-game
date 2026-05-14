"""Conversation and inline-detail rendering for slide scenes."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_base import escape
from src.game.reporting.scenes import Scene
from src.game.reporting.slides.cast import display_name
from src.game.reporting.slides.scene_inline import (
    _audience_chip,
    _delta_chip,
    _inline_background_activity,
    _inline_mechanics,
    _inline_memories,
    _intent_label,
    _interruption_inset,
    _render_menu_options,
    _turn_pill,
)
from src.game.reporting.slides.scene_titles import _conversation_target


def _conversation_body(scene: Scene) -> str:
    target_name = display_name(_conversation_target(scene.records))
    cards: list[str] = []
    prev_menu: dict[str, Any] | None = None
    for record in scene.records:
        # Pre-exchange: NPC interruptions render as their own inset above the exchange
        interruption_inset = _interruption_inset(record)
        if interruption_inset:
            cards.append(interruption_inset)
        exchange = record.get("exchange")
        chosen = str(
            (record.get("mechanical_result", {}).get("action", {}) or {}).get("intent_id") or ""
        )
        if isinstance(exchange, dict):
            cards.append(_exchange_turn_card(record, exchange, target_name, prev_menu, chosen))
        elif _record_has_any_turn_data(record):
            cards.append(_silent_turn_card(record, target_name, prev_menu, chosen))
        # Update prev_menu only if this record has a follow_up_menu
        next_menu = record.get("follow_up_menu")
        if isinstance(next_menu, dict):
            prev_menu = next_menu
    if not cards:
        return "<p class='muted'>No dialogue recorded.</p>"
    return f"<div class='chat'>{''.join(cards)}</div>"


def _record_has_any_turn_data(record: dict[str, Any]) -> bool:
    """True if this turn has mechanics, pull, or memories even without an exchange."""
    result = record.get("mechanical_result") or {}
    if isinstance(result.get("chance_breakdown"), dict):
        return True
    if isinstance(result.get("pull_attempt"), dict):
        return True
    commits = record.get("agent_commits") or {}
    if isinstance(commits, dict):
        if commits.get("curator_batches"):
            return True
    return False


def _silent_turn_card(
    record: dict[str, Any],
    npc_name: str,
    offered_menu: dict[str, Any] | None,
    chosen_intent: str,
) -> str:
    """Render a turn card for a turn that has details but no exchange."""
    result = record.get("mechanical_result") or {}
    action = result.get("action") or {}
    kind = str(action.get("kind") or "")
    target = action.get("target_id") or ""
    summary = f"{kind.replace('_', ' ').title()}"
    if target:
        summary += f" → {display_name(str(target))}"
    elif npc_name:
        summary += f" → {npc_name}"
    turn_pill = _turn_pill(record)
    inline_blocks = _inline_blocks_for_record(record, offered_menu, chosen_intent, open_first=True)

    return (
        "<div class='exchange'>"
        f"<div class='exchange-header'>{turn_pill}"
        f"<span class='muted small'>{escape(summary)}</span></div>"
        f"{inline_blocks}"
        "</div>"
    )


def _exchange_turn_card(
    record: dict[str, Any],
    exchange: dict[str, Any],
    npc_name: str,
    offered_menu: dict[str, Any] | None,
    chosen_intent: str,
) -> str:
    player_line = str(exchange.get("player_dialogue") or "").strip()
    npc_line = str(exchange.get("npc_dialogue") or "").strip()
    tone = str(exchange.get("npc_tone") or "")
    mood_after = str(exchange.get("npc_mood_after") or "")
    result = record.get("mechanical_result") or {}
    success = result.get("success") is True
    deltas_text = _delta_chip(result)
    audience_text = _audience_chip(result)
    action = result.get("action") or {}
    intent_id = action.get("intent_id") or ""
    intent_pill = (
        f"<span class='intent-pill'>{escape(_intent_label(str(intent_id)))}</span>"
        if intent_id
        else ""
    )
    outcome_class = "success" if success else "miss"
    outcome_label = "landed" if success else "missed"
    mood_pill = f"<span class='outcome-pill'>{escape(mood_after)}</span>" if mood_after else ""
    tone_pill = f"<span class='outcome-pill'>{escape(tone)}</span>" if tone else ""
    chips = "".join(
        [
            intent_pill,
            f"<span class='outcome-pill {outcome_class}'>{outcome_label}</span>",
            tone_pill,
            mood_pill,
            deltas_text,
            audience_text,
        ]
    )

    turn_pill = _turn_pill(record)
    inline_blocks = _inline_blocks_for_record(record, offered_menu, chosen_intent)

    return (
        "<div class='exchange'>"
        f"<div class='exchange-header'>{turn_pill}</div>"
        f"<div class='bubble player'>{escape(player_line) or '<em>…</em>'}</div>"
        f"<div class='bubble npc'><div class='npc-tag'>{escape(npc_name)}</div>"
        f"{escape(npc_line) or '<em>…</em>'}</div>"
        f"<div class='exchange-outcome'>{chips}</div>"
        f"{inline_blocks}"
        "</div>"
    )


def _inline_blocks_for_record(
    record: dict[str, Any],
    offered_menu: dict[str, Any] | None,
    chosen_intent: str,
    *,
    open_first: bool = False,
) -> str:
    """Build the inline collapsible stack for a turn."""
    blocks: list[str] = []
    mech_html = _inline_mechanics(record)
    if mech_html:
        attrs = " open" if open_first else ""
        blocks.append(
            f"<details class='inline-detail'{attrs}><summary>Why this outcome?</summary>"
            f"<div class='inline-body'>{mech_html}</div></details>"
        )
    if offered_menu:
        menu_html = _render_menu_options(offered_menu, chosen_intent)
        if menu_html:
            blocks.append(
                f"<details class='inline-detail'><summary>Menu offered</summary>"
                f"<div class='inline-body'>{menu_html}</div></details>"
            )
    mem_html = _inline_memories(record)
    if mem_html:
        blocks.append(
            f"<details class='inline-detail'><summary>Memories formed</summary>"
            f"<div class='inline-body'>{mem_html}</div></details>"
        )
    bg_html = _inline_background_activity(record)
    if bg_html:
        blocks.append(
            f"<details class='inline-detail bg-detail'><summary>Meanwhile around the villa</summary>"
            f"<div class='inline-body'>{bg_html}</div></details>"
        )
    return "".join(blocks)
