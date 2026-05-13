"""Self-contained HTML rendering for review packets."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_arrivals import arrival_roll_block
from src.game.reporting.html_audience import audience_block
from src.game.reporting.html_base import escape, index_page, page, table_page
from src.game.reporting.html_blocks import (
    agent_commit_block,
    autopilot_block,
    casa_amor_block,
    couple_status_block,
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
from src.game.reporting.html_events import (
    challenge_block,
    group_date_block,
    producer_text_block,
    revealed_preferences_block,
)
from src.game.reporting.html_gather import pending_gather_block
from src.game.reporting.html_math import math_block
from src.game.reporting.stylish.session import stylish_session_page


def session_page(
    title: str,
    records: list[dict[str, Any]],
    preface: str = "",
    reviewer_notes: list[dict[str, object]] | None = None,
) -> str:
    """Render one session trace using the default stylish renderer."""
    return stylish_session_page(title, records, preface=preface, reviewer_notes=reviewer_notes)


def session_page_minimal(title: str, records: list[dict[str, Any]], preface: str = "") -> str:
    """Render one session trace as turn cards.

    ``preface`` is optional self-contained HTML inserted above the first turn.
    Preview reports use it to disclose pre-warmed state or mock-mode details.
    """
    cards = []
    if preface:
        cards.append(f"<section class='card'>{preface}</section>")
    collapsible = len(records) >= 30
    for record in records:
        cards.append(_turn_card(record, collapsible=collapsible))
    return page(title, "".join(cards))


def _turn_card(record: dict[str, Any], *, collapsible: bool) -> str:
    result = record["mechanical_result"]
    action = result["action"]
    outcome_class = "success" if result["success"] else "miss"
    header = (
        f"Turn {record['turn']} - Day {record['day']} - "
        f"{escape(record['phase'])} - {escape(record['location'])}"
    )
    open_attr = "" if collapsible else " open"
    return (
        f"<details class='turn' id='turn-{escape(record['turn'])}'{open_attr}>"
        f"<summary>{header}</summary>"
        f"<p class='meta'>{escape(record.get('visible_state', ''))}</p>"
        f"{villa_snapshot_block(record.get('villa_snapshot'))}"
        f"{time_block(record)}"
        f"{casa_amor_block(record)}"
        f"{couple_status_block(record)}"
        f"{challenge_block(record.get('challenge'))}"
        f"{producer_text_block(record.get('producer_text'))}"
        f"{pending_gather_block(record)}"
        f"{group_date_block(record.get('group_date'))}"
        f"{revealed_preferences_block(record.get('revealed_preferences'))}"
        f"<p><b>You chose:</b> {escape(action['kind'])} "
        f"{escape(str(action.get('target_id') or ''))} "
        f"{escape(str(action.get('intent_id') or ''))}</p>"
        f"{autopilot_block(record.get('agent_commits'))}"
        f"{math_block(result)}"
        f"{pull_attempt_block(result.get('pull_attempt'))}"
        f"{arrival_roll_block(record)}"
        f"{exchange_block(record.get('exchange'))}"
        f"{event_block(record.get('event_narration'))}"
        f"{audience_block(record.get('audience_snapshot'))}"
        f"{follow_up_block(record.get('follow_up_menu'))}"
        f"{interruption_block(record)}"
        f"{agent_commit_block(record.get('agent_commits'))}"
        f"{memory_block(record.get('agent_commits'))}"
        f"<p><b>Roll:</b> {escape(str(result.get('roll')))} vs "
        f"{escape(str(result.get('success_chance')))} "
        f"<span class='{outcome_class}'>{'Success' if result['success'] else 'Miss'}</span></p>"
        f"<p><b>Deltas:</b> {escape(delta_text(result))}</p>"
        f"<p><b>Hash:</b> <code>{escape(record['output_hash'])}</code></p>"
        "</details>"
    )


__all__ = ["escape", "index_page", "page", "session_page", "session_page_minimal", "table_page"]
