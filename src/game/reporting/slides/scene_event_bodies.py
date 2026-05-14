"""Non-conversation body renderers for slide scenes."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_base import escape
from src.game.reporting.scenes import Scene
from src.game.reporting.slides.cast import display_name
from src.game.reporting.slides.scene_inline import _inline_mechanics, _inline_memories
from src.game.reporting.slides.scene_titles import _ceremony_title, _challenge_title


def _ceremony_body(scene: Scene) -> str:
    # Detect finale (final_vote ceremony) and render specially
    is_finale = False
    for record in scene.records:
        events = record.get("ceremony_events") or []
        for ev in events:
            if isinstance(ev, dict) and ev.get("kind") == "final_vote":
                is_finale = True
                break
        if is_finale:
            break

    blocks: list[str] = []
    for record in scene.records:
        narration = record.get("event_narration")
        events = record.get("ceremony_events") if isinstance(record.get("ceremony_events"), list) else []
        # Surface event messages (e.g. "Dumping decision: maya leaves the villa.")
        event_message_lines: list[str] = []
        for ev in events:
            if isinstance(ev, dict):
                msg = str(ev.get("message") or "").strip()
                if msg:
                    event_message_lines.append(msg)
        label_parts = [
            _ceremony_title(str(ev.get("kind") or ""), record.get("day"))
            for ev in events
            if isinstance(ev, dict) and ev.get("kind")
        ]
        label = " · ".join(p for p in label_parts if p) or "Ceremony"
        prose = str(narration.get("prose") or "").strip() if isinstance(narration, dict) else ""

        feature_class = "ceremony-feature finale" if is_finale else "ceremony-feature"
        messages_html = (
            "<div class='ceremony-events'>"
            + "".join(f"<div class='ceremony-event'>· {escape(m)}</div>" for m in event_message_lines)
            + "</div>"
            if event_message_lines
            else ""
        )
        prose_html = f"<div class='prose'>{escape(prose)}</div>" if prose else ""
        if prose or event_message_lines:
            blocks.append(
                f"<div class='{feature_class}'>"
                f"<div class='label'>{escape(label)}</div>"
                f"{prose_html}{messages_html}"
                f"</div>"
            )
    if not blocks:
        return "<p class='muted'>No narration recorded for this ceremony.</p>"
    return "".join(blocks)


# ============================================================================
# Challenge
# ============================================================================


def _challenge_body(scene: Scene) -> str:
    blocks: list[str] = []
    for record in scene.records:
        chal = record.get("challenge")
        if not isinstance(chal, dict):
            continue
        kind = str(chal.get("kind") or "")
        name = _challenge_title(kind)
        result = chal.get("result") or ""
        deltas = chal.get("deltas") or {}
        stat = str(chal.get("stat_tested") or chal.get("stat") or "")
        result_class = "success" if result == "success" else "miss"
        result_label = "Success" if result == "success" else ("Miss" if result else "Pending")
        delta_summary = _challenge_delta_summary(deltas)
        stat_html = f"<span class='muted small'>tested {escape(stat)}</span>" if stat else ""
        mech_html = _inline_mechanics(record)
        mech_block = (
            f"<details class='inline-detail'><summary>Why this outcome?</summary>"
            f"<div class='inline-body'>{mech_html}</div></details>"
            if mech_html else ""
        )
        blocks.append(
            f"<div class='challenge-feature'>"
            f"<div class='label'>Daily challenge</div>"
            f"<div class='name'>{escape(name)} {stat_html}</div>"
            f"<div class='summary'><span class='outcome-pill {result_class}'>{result_label}</span>"
            f"{(' &middot; ' + delta_summary) if delta_summary else ''}</div>"
            f"{mech_block}"
            f"</div>"
        )
    # Trailing producer text in same scene
    for record in scene.records:
        producer = record.get("producer_text")
        if isinstance(producer, dict):
            body = str(producer.get("body") or "").strip()
            if body:
                blocks.append(
                    f"<div class='challenge-feature' style='border-left:4px solid var(--accent)'>"
                    f"<div class='label'>Producer text</div>"
                    f"<div class='summary'>{escape(body)}</div></div>"
                )
    return "".join(blocks) or "<p class='muted'>Challenge fired but no details recorded.</p>"


def _challenge_delta_summary(deltas: dict[str, Any]) -> str:
    if not isinstance(deltas, dict):
        return ""
    parts: list[str] = []
    for target, delta in deltas.items():
        if not isinstance(delta, dict):
            continue
        for key, val in delta.items():
            if not isinstance(val, (int, float)) or val == 0:
                continue
            sign = "+" if val > 0 else ""
            parts.append(f"{escape(display_name(target))} {escape(key)} {sign}{int(val)}")
    return ", ".join(parts)


# ============================================================================
# Gather
# ============================================================================


def _gather_body(scene: Scene) -> str:
    blocks: list[str] = []
    for record in scene.records:
        producer = record.get("producer_text")
        if isinstance(producer, dict):
            body = str(producer.get("body") or "").strip()
            if body:
                blocks.append(
                    f"<div class='ceremony-feature'>"
                    f"<div class='label'>I've got a text</div>"
                    f"<div class='prose'>{escape(body)}</div></div>"
                )
        pending = record.get("pending_gather")
        if isinstance(pending, dict):
            kind = str(pending.get("kind") or "")
            loc = str(pending.get("gather_location") or "")
            if kind or loc:
                blocks.append(
                    f"<div class='ceremony-feature' style='padding:16px 22px;'>"
                    f"<div class='label'>{escape(kind.replace('_', ' ').title())}</div>"
                    f"<p class='muted'>Everyone gathers at the <b>"
                    f"{escape(display_name(loc))}</b>.</p></div>"
                )
        narration = record.get("event_narration")
        if isinstance(narration, dict):
            prose = str(narration.get("prose") or "")
            if prose:
                blocks.append(
                    f"<div class='ceremony-feature'><div class='prose'>{escape(prose)}</div></div>"
                )
    return "".join(blocks) or "<p class='muted'>The villa gathers.</p>"


# ============================================================================
# Background
# ============================================================================


def _background_body(scene: Scene) -> str:
    vignettes: list[str] = []
    for record in scene.records:
        commits = record.get("agent_commits")
        if not isinstance(commits, dict):
            continue
        dialogues = commits.get("background_dialogues")
        if not isinstance(dialogues, list):
            continue
        villa = commits.get("villa_update") or {}
        location_lookup: list[str] = []
        starts = villa.get("conversation_starts") or [] if isinstance(villa, dict) else []
        continues_list = (
            villa.get("conversation_continues") or [] if isinstance(villa, dict) else []
        )
        for start in starts:
            if isinstance(start, dict):
                location_lookup.append(str(start.get("location") or ""))
        for cont in continues_list:
            if isinstance(cont, dict):
                location_lookup.append("")
        for idx, exchange in enumerate(dialogues):
            if not isinstance(exchange, dict):
                continue
            line_a = str(exchange.get("speaker_a_line") or "").strip()
            line_b = str(exchange.get("speaker_b_line") or "").strip()
            tone = str(exchange.get("tone") or "")
            loc = location_lookup[idx] if idx < len(location_lookup) else ""
            where = (
                f"{escape(display_name(loc))} · {escape(tone)}" if loc else escape(tone)
            )
            vignettes.append(
                "<div class='bg-vignette'>"
                f"<div class='where'>{where}</div>"
                f"<div class='line'>{escape(line_a)}</div>"
                f"<div class='line'>{escape(line_b)}</div>"
                "</div>"
            )
        # Inline memories from background turns too
        mem_html = _inline_memories(record)
        if mem_html:
            vignettes.append(
                f"<details class='inline-detail'><summary>Memories formed</summary>"
                f"<div class='inline-body'>{mem_html}</div></details>"
            )
    return "".join(vignettes) or "<p class='muted'>Quiet villa moment.</p>"


# ============================================================================
# Movement
# ============================================================================


def _movement_body(scene: Scene) -> str:
    lines: list[str] = []
    for record in scene.records:
        commits = record.get("agent_commits")
        if not isinstance(commits, dict):
            continue
        villa = commits.get("villa_update")
        if not isinstance(villa, dict):
            continue
        movements = villa.get("npc_movements") or []
        for m in movements:
            if not isinstance(m, dict):
                continue
            who = display_name(str(m.get("npc_id") or ""))
            where = display_name(str(m.get("target_location") or ""))
            reason = str(m.get("reason") or "").replace("_", " ")
            lines.append(
                f"<div class='bg-vignette'>"
                f"<div class='line'>{escape(who)} drifts to the <b>{escape(where)}</b>"
                f" <span class='muted'>· {escape(reason)}</span></div></div>"
            )
    return "".join(lines) or "<p class='muted'>People shifting around the villa.</p>"


# ============================================================================
# Day boundary
# ============================================================================


def _day_boundary_body(scene: Scene) -> str:
    recap_items: list[str] = []
    for record in scene.records:
        recaps = record.get("daily_recaps")
        if isinstance(recaps, list):
            for r in recaps:
                if isinstance(r, dict):
                    line = str(r.get("body") or r.get("text") or "").strip()
                    day = r.get("day")
                    if line:
                        prefix = (
                            f"<span class='muted'>Day {escape(day)}</span> · "
                            if day is not None
                            else ""
                        )
                        recap_items.append(f"<div class='recap-item'>{prefix}{escape(line)}</div>")
    audience: list[str] = []
    for record in scene.records:
        snap = record.get("audience_snapshot")
        if isinstance(snap, dict):
            rankings = snap.get("ranking")
            if isinstance(rankings, list):
                for rank in rankings:
                    if isinstance(rank, dict):
                        label = str(rank.get("label") or "")
                        score = rank.get("score")
                        if label:
                            audience.append(
                                f"<div class='recap-item'><b>#{escape(rank.get('rank', ''))}</b> "
                                f"{escape(label)} <span class='muted'>· {escape(score)}</span></div>"
                            )
    blocks: list[str] = []
    if recap_items:
        blocks.append(
            f"<div class='recap-feature'><h3>While you were busy</h3>{''.join(recap_items)}</div>"
        )
    if audience:
        blocks.append(
            f"<div class='recap-feature' style='border-left-color:var(--gold)'>"
            f"<h3>Audience standings</h3>{''.join(audience)}</div>"
        )
    return "".join(blocks) or "<p class='muted'>Day wraps quietly.</p>"


# ============================================================================
# Generic turn
# ============================================================================


def _turn_body(scene: Scene) -> str:
    lines: list[str] = []
    for record in scene.records:
        result = record.get("mechanical_result") or {}
        action = result.get("action") or {}
        kind = str(action.get("kind") or "")
        target = display_name(str(action.get("target_id") or "")) if action.get("target_id") else ""
        success = result.get("success") is True
        outcome_class = "success" if success else "miss"
        label = kind.replace("_", " ").title()
        target_label = f" → {escape(target)}" if target else ""
        lines.append(
            f"<div class='bg-vignette'><div class='line'>{escape(label)}{target_label} "
            f"<span class='outcome-pill {outcome_class}'>"
            f"{('ok' if success else 'miss')}</span></div></div>"
        )
    return "".join(lines)
