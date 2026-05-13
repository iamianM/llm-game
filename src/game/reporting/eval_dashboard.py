"""HTML dashboard for playthrough eval reports."""

from __future__ import annotations

from src.game.eval.playthrough import PlaythroughReport
from src.game.reporting.html import escape
from src.game.reporting.stylish.css import STYLISH_CSS


def playthrough_eval_page(report: PlaythroughReport) -> str:
    """Render a playthrough eval report as self-contained HTML."""
    assertion_cards = "".join(
        "<section class='card'>"
        f"<h2 class='{'success' if assertion.passed else 'miss'}'>"
        f"{escape('PASS' if assertion.passed else 'FAIL')} - {escape(assertion.label)}</h2>"
        f"<p>{escape(assertion.detail)}</p>"
        f"{_turn_links(assertion.interesting_turns)}"
        "</section>"
        for assertion in report.assertions
    )
    stats = report.stats
    stats_rows = [
        ("Turns", stats.turns),
        ("Conversations started", stats.conversations_started),
        ("Wheel exits", stats.wheel_exits),
        ("Walk aways", stats.walk_aways),
        ("Pull attempts", stats.pull_attempts),
        ("Pull failures", stats.pull_failures),
        ("Interruptions fired", stats.interruptions_fired),
        ("Interruption responses", stats.interruption_responses),
        ("Interruption response kinds", ", ".join(stats.interruption_response_kinds) or "none"),
        ("Memories created", stats.memories_created),
        ("Background dialogues", stats.background_dialogues),
        ("Gossip picks", stats.gossip_picks),
        ("Low-chance rolls", stats.low_chance_rolls),
        ("Ceremony events", stats.ceremony_events),
        ("Audience snapshots", stats.audience_snapshots),
        ("Challenges completed", stats.challenges_completed),
        ("Challenges succeeded", stats.challenges_succeeded),
        ("Producer texts", stats.producer_texts_fired),
        ("Group date turns", stats.group_dates_held),
        ("Revealed preferences", stats.revealed_preference_count),
        ("Compatibility bonus rolls", stats.compatibility_bonus_observed),
        ("Max couple strength", stats.max_couple_strength_reached),
        ("Hideaway used", stats.hideaway_used),
        ("Steal attempts", stats.steal_attempts_total),
        ("Steal successes", stats.steal_successes),
        ("Casa Amor visited", stats.casa_amor_visited),
        ("Casa Amor decision", stats.casa_amor_player_decision or "none"),
        ("Casa Amor partners swapped", stats.casa_amor_partners_swapped),
        ("Casa Amor perception swing", stats.casa_amor_perception_swing),
        ("Autopilot actions", stats.autopilot_actions_total),
        ("Autopilot rationales", f"{stats.autopilot_rationales_present}/{stats.autopilot_actions_total}"),
        ("Autopilot confidence", stats.autopilot_confidence_counts),
        ("Auto advances", stats.auto_advances_total),
        ("Avg actions per phase", stats.avg_actions_per_phase),
        ("Arrival rolls", stats.arrival_rolls_total),
        ("Arrival interrupt hits", stats.arrival_interrupt_hits),
        ("Arrival pull hits", stats.arrival_pull_hits),
        ("NPC summons", stats.npc_summoned_total),
        ("NPC left menus", stats.npc_left_total),
        ("Final day", stats.final_day),
        ("Outcome", stats.outcome or "none"),
    ]
    stats_html = "".join(
        f"<tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>"
        for label, value in stats_rows
    )
    rates = "".join(
        f"<li>{escape(category)}: {escape(rate)}</li>"
        for category, rate in stats.success_rate_by_category.items()
    )
    body = (
        f"<p><b>Result:</b> {report.passed} passed, {report.failed} failed.</p>"
        f"<p><b>Trace:</b> <code>{escape(report.trace_path)}</code></p>"
        f"<p><a href='session.html'>Open session.html</a></p>"
        f"<section class='card'><h2>Aggregate Stats</h2><table>{stats_html}</table>"
        f"<h3>Success rate by category</h3><ul>{rates or '<li>none</li>'}</ul></section>"
        f"<section class='card'><h2>Interesting Turns</h2>{_turn_links(report.interesting_turns)}</section>"
        f"<div class='grid'>{assertion_cards}</div>"
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>Playthrough Eval</title><style>{STYLISH_CSS}</style></head>"
        f"<body><main class='shell'><header class='hero'><h1>Playthrough Eval</h1></header>{body}</main></body></html>"
    )


def _turn_links(turns: list[int]) -> str:
    if not turns:
        return "<p class='meta'>No turns flagged.</p>"
    links = " ".join(
        f"<a class='pill' href='session.html#turn-{turn}'>Turn {turn}</a>"
        for turn in turns
    )
    return f"<p>{links}</p>"
