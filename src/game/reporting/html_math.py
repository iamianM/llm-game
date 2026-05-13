"""Success-math HTML blocks."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_base import escape


def math_block(result: dict[str, Any]) -> str:
    """Render the chance formula and roll result."""
    roll = result.get("roll")
    chance = result.get("success_chance")
    if not isinstance(roll, int) or not isinstance(chance, int):
        return ""
    outcome = "success" if result.get("success") else "miss"
    tags = result.get("tags")
    tag_text = ", ".join(str(tag) for tag in tags) if isinstance(tags, list) else "none"
    breakdown = _chance_breakdown_text(result.get("chance_breakdown"), chance)
    return (
        "<div class='card math'>"
        "<p><b>Success math</b></p>"
        f"<p>{breakdown}</p>"
        f"<p>Rolled {roll}. Outcome: "
        f"<span class='{'success' if outcome == 'success' else 'miss'}'>{escape(outcome)}</span>.</p>"
        f"<p class='meta'>Tags: {escape(tag_text)}</p>"
        "</div>"
    )


def _chance_breakdown_text(breakdown: object, fallback_chance: int) -> str:
    if not isinstance(breakdown, dict):
        return f"Final chance {fallback_chance}%."
    stat_name = breakdown.get("stat_name") or "stat"
    parts = [
        f"base {escape(breakdown.get('base', 0))}",
        (
            f"{escape(stat_name)} {escape(breakdown.get('stat_value'))} x "
            f"{escape(breakdown.get('stat_multiplier'))} = "
            f"{escape(breakdown.get('stat_contribution'))}"
        ),
        (
            f"affection {escape(breakdown.get('affection_value'))} / "
            f"{escape(breakdown.get('affection_divisor'))} = "
            f"{escape(breakdown.get('affection_contribution'))}"
        ),
    ]
    risk = breakdown.get("risk")
    if risk is not None:
        parts.append(f"risk {escape(risk)}: {escape(_signed(breakdown.get('risk_modifier')))}")
    mood_modifier = breakdown.get("mood_modifier")
    if isinstance(mood_modifier, int) and mood_modifier != 0:
        parts.append(f"mood {escape(_signed(mood_modifier))}")
    compatibility = breakdown.get("compatibility_bonus")
    if isinstance(compatibility, int) and compatibility:
        parts.append(f"compatibility {escape(_signed(compatibility))}")
    penalty = breakdown.get("dealbreaker_penalty")
    if isinstance(penalty, int) and penalty:
        parts.append(f"dealbreaker -{escape(penalty)}")
    return (
        f"{' + '.join(parts)} = {escape(breakdown.get('pre_cap'))}"
        f"{_cap_text(breakdown)}. Final chance {escape(breakdown.get('final_chance', fallback_chance))}%."
    )


def _cap_text(breakdown: dict[str, object]) -> str:
    pre_cap = breakdown.get("pre_cap")
    cap = breakdown.get("cap")
    floor = breakdown.get("floor")
    if isinstance(pre_cap, int) and isinstance(cap, int) and pre_cap > cap:
        return f", capped at {cap}"
    if isinstance(pre_cap, int) and isinstance(floor, int) and pre_cap < floor:
        return f", floored at {floor}"
    return ""


def _signed(value: object) -> str:
    if not isinstance(value, int):
        return str(value)
    return f"+{value}" if value >= 0 else str(value)
