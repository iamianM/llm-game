"""HTML report for golden LLM eval runs."""

from __future__ import annotations

from typing import Any

from src.game.eval.golden_models import GoldenEvalRun, GoldenScenarioResult, GoldenTurnResult
from src.game.eval.golden_report_agents import actual_agent_tool_responses, expected_agent_tools
from src.game.eval.golden_report_assets import report_css, report_script
from src.game.reporting.html_base import escape


def render_golden_eval_html(run: GoldenEvalRun) -> str:
    """Render a self-contained, reviewer-focused golden eval report."""
    body = (
        _hero(run)
        + _toolbar()
        + _scenario_nav(run)
        + "".join(
            _scenario_block(index + 1, scenario, llm_mode=run.llm_mode)
            for index, scenario in enumerate(run.scenarios)
        )
        + report_script()
    )
    return _page("Golden LLM Eval", body)


def _page(title: str, body: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{escape(title)}</title><style>{report_css()}</style></head>"
        f"<body><main><h1>{escape(title)}</h1>{body}</main></body></html>"
    )


def _hero(run: GoldenEvalRun) -> str:
    total_turns = sum(len(scenario.turns) for scenario in run.scenarios)
    failed_turns = sum(
        1
        for scenario in run.scenarios
        for turn in scenario.turns
        if any(check.result == "fail" for check in turn.checks)
    )
    return (
        "<section class='hero'>"
        "<div>"
        "<p class='eyebrow'>Review packet</p>"
        "<h2>Golden LLM Eval</h2>"
        "<p class='lede'>Human-readable scenario results, goldens, checks, dialogue, memories, "
        "event narration, judge findings, and model reasoning summaries.</p>"
        "</div>"
        "<div class='metrics'>"
        f"{_metric('Mode', run.llm_mode)}"
        f"{_metric('Judge', 'on' if run.judge_enabled else 'off')}"
        f"{_metric('Scenarios', run.scenario_count)}"
        f"{_metric('Workers', run.worker_count)}"
        f"{_metric('Turns', total_turns)}"
        f"{_metric('Passed', run.passed, 'pass')}"
        f"{_metric('Failed', run.failed, 'fail')}"
        f"{_metric('Failed turns', failed_turns, 'fail' if failed_turns else 'pass')}"
        "</div></section>"
    )


def _toolbar() -> str:
    return (
        "<section class='toolbar'>"
        "<div class='filters' aria-label='Status filters'>"
        "<button data-filter='all' class='active'>All</button>"
        "<button data-filter='fail'>Fail</button>"
        "<button data-filter='cannot_determine'>Cannot determine</button>"
        "<button data-filter='pass'>Pass</button>"
        "</div>"
        "<input id='search' type='search' placeholder='Search scenario, turn, check, NPC, intent...'>"
        "<div class='filters'>"
        "<select id='sortMode' aria-label='Sort scenarios'>"
        "<option value='default'>Original order</option>"
        "<option value='status'>Failures first</option>"
        "<option value='title'>Title</option>"
        "<option value='turns'>Most turns</option>"
        "</select>"
        "<button id='expandFailures'>Open failures</button>"
        "<button id='collapseAll'>Collapse all</button>"
        "</div>"
        "</section>"
    )


def _scenario_nav(run: GoldenEvalRun) -> str:
    links = "".join(
        "<a class='nav-item' "
        f"data-status='{escape(scenario.status)}' "
        f"data-index='{index}' data-title='{escape(scenario.title.lower())}' "
        f"data-turns='{len(scenario.turns)}' data-failures='{len(_failed_checks(scenario))}' "
        f"href='#{escape(scenario.id)}'>"
        f"<span>{escape(scenario.title)}</span>{_badge(scenario.status)}</a>"
        for index, scenario in enumerate(run.scenarios, start=1)
    )
    return f"<nav class='scenario-nav'>{links}</nav>"


def _scenario_block(index: int, scenario: GoldenScenarioResult, *, llm_mode: str) -> str:
    failed = _failed_checks(scenario)
    checks = sorted({check.id for turn in scenario.turns for check in turn.checks})
    checked = ", ".join(checks)
    turns = "".join(_turn_block(turn) for turn in scenario.turns)
    return (
        f"<section id='{escape(scenario.id)}' class='scenario' data-status='{escape(scenario.status)}' "
        f"data-index='{index}' data-title='{escape(scenario.title.lower())}' "
        f"data-turns='{len(scenario.turns)}' data-failures='{len(failed)}'>"
        "<div class='scenario-head'>"
        f"<div><p class='eyebrow'>Scenario {index}</p><h2>{escape(scenario.title)}</h2>"
        f"<p>{escape(scenario.goal)}</p></div>"
        f"<div class='scenario-head-tags'>{_mode_badge(llm_mode)}{_badge(scenario.status)}</div>"
        "</div>"
        "<div class='scenario-meta'>"
        f"<span>{len(scenario.turns)} turns</span>"
        f"<span>{len(failed)} failing checks</span>"
        f"<span title='{escape(checked)}'>Checks: {escape(checked or 'none')}</span>"
        "</div>"
        f"{_failure_summary(failed)}"
        f"<div class='turn-list'>{turns}</div>"
        "</section>"
    )


def _mode_badge(llm_mode: str) -> str:
    label = "Real LLM" if llm_mode == "real" else "Mock"
    tooltip = (
        "Real LLM mode: agent calls hit the live model."
        if llm_mode == "real"
        else "Mock mode: deterministic stand-in output; live-only checks auto-pass and are clearly labeled."
    )
    return (
        f"<span class='badge mode-{escape(llm_mode)}' title='{escape(tooltip)}'>"
        f"{escape(label)}</span>"
    )


def _turn_block(turn: GoldenTurnResult) -> str:
    status = _turn_status(turn)
    checks = "".join(_check_row(check.model_dump(mode="json")) for check in turn.checks)
    failed = any(check.result == "fail" for check in turn.checks)
    record = turn.record or {}
    open_attr = " open" if failed or turn.error else ""
    return (
        f"<details class='turn' data-status='{escape(status)}'{open_attr}>"
        f"<summary><span>{escape(turn.id)}</span>{_badge(status)}"
        f"<small>{escape(_action_label(turn.action))}</small></summary>"
        f"{_error(turn.error)}"
        f"{_golden_contract(turn)}"
        f"<section><h3>Checks</h3><div class='checks'>{checks}</div></section>"
        f"{_actual_output(record)}"
        f"{actual_agent_tool_responses(record)}"
        "</details>"
    )


def _golden_contract(turn: GoldenTurnResult) -> str:
    judge_items = "".join(
        f"<li><b>{escape(check.id)}</b>: {escape(check.criteria)}</li>"
        for check in turn.judge_checks
    )
    judges = (
        f"<div class='contract-card'><b>Judge checks</b><ul class='compact'>{judge_items}</ul></div>"
        if judge_items
        else ""
    )
    return (
        "<section><h3>Golden Tools / Expected Response</h3>"
        "<div class='golden-grid'>"
        "<div class='contract-card'><b>Expected tool calls</b>"
        f"{expected_agent_tools(turn.action, turn.expected_tools)}</div>"
        f"{_arrangements(turn.arrangements)}"
        f"<div class='contract-card'><b>Expected response</b><p class='golden'>{escape((turn.golden or '').strip())}</p></div>"
        f"{judges}"
        "</div></section>"
    )


def _arrangements(raw: dict[str, Any]) -> str:
    if not raw:
        return ""
    rows = []
    player_location = raw.get("player_location")
    if player_location:
        rows.append(f"<li><b>player</b>: {escape(player_location)}</li>")
    npc_locations = raw.get("npc_locations")
    if isinstance(npc_locations, dict):
        rows.extend(
            f"<li><b>{escape(npc_id)}</b>: {escape(location)}</li>"
            for npc_id, location in npc_locations.items()
        )
    active = raw.get("active_conversation")
    if isinstance(active, dict):
        rows.append(f"<li><b>active conversation</b>: {escape(active.get('target_id', 'unknown'))}</li>")
        pending = active.get("pending_interruption")
        if isinstance(pending, dict):
            rows.append(
                "<li><b>pending interruption</b>: "
                f"{escape(pending.get('interrupter_id', 'unknown'))} "
                f"({escape(pending.get('reason', 'unknown'))}, {escape(pending.get('urgency', 'unknown'))})</li>"
            )
        options = active.get("pending_options")
        if isinstance(options, list):
            for option in options:
                if isinstance(option, dict):
                    rows.append(
                        "<li><b>wheel option</b>: "
                        f"{escape(option.get('label', ''))} "
                        f"[{escape(option.get('category', ''))} / {escape(option.get('intent_kind', ''))}]</li>"
                    )
    return f"<div class='contract-card'><b>Arranged preconditions</b><ul class='compact'>{''.join(rows)}</ul></div>"


def _actual_output(record: dict[str, Any]) -> str:
    if not record:
        return ""
    parts = [
        _mechanical_result(record.get("mechanical_result")),
        _exchange(record.get("exchange")),
        _follow_up_menu(record.get("follow_up_menu")),
        _event_narration(record.get("event_narration")),
        _ceremony_events(record.get("ceremony_events")),
        _memories(record.get("agent_commits")),
        _resort_changes(record.get("agent_commits")),
    ]
    rendered = "".join(part for part in parts if part)
    if not rendered:
        return ""
    return f"<section><h3>Actual output</h3>{rendered}</section>"


def _mechanical_result(raw: object) -> str:
    if not isinstance(raw, dict):
        return ""
    success = raw.get("success")
    tags = raw.get("tags")
    chance = raw.get("success_chance")
    roll = raw.get("roll")
    deltas = _relationship_deltas(raw.get("relationship_deltas"))
    bits = [f"Success: {_yes_no(success)}"]
    if chance is not None:
        bits.append(f"Chance: {chance}")
    if roll is not None:
        bits.append(f"Roll: {roll}")
    if isinstance(tags, list) and tags:
        bits.append("Tags: " + ", ".join(str(tag) for tag in tags))
    return f"<div class='fact-card'><b>Engine result</b><p>{escape(' | '.join(bits))}</p>{deltas}</div>"


def _relationship_deltas(raw: object) -> str:
    if not isinstance(raw, dict) or not raw:
        return ""
    rows = []
    for target, delta in raw.items():
        if not isinstance(delta, dict):
            continue
        changed = [f"{key} {value:+d}" for key, value in delta.items() if isinstance(value, int) and value]
        if changed:
            rows.append(f"<li><b>{escape(target)}</b>: {escape(', '.join(changed))}</li>")
    return f"<ul class='compact'>{''.join(rows)}</ul>" if rows else ""


def _exchange(raw: object) -> str:
    if not isinstance(raw, dict):
        return ""
    return (
        "<div class='dialogue'>"
        f"<p><b>Player</b><span>{escape(raw.get('player_dialogue', ''))}</span></p>"
        f"<p><b>NPC</b><span>{escape(raw.get('npc_dialogue', ''))}</span></p>"
        f"<p class='muted'>Tone: {escape(raw.get('npc_tone', 'unknown'))}; "
        f"mood after: {escape(raw.get('npc_mood_after', 'unknown'))}</p>"
        "</div>"
    )


def _follow_up_menu(raw: object) -> str:
    if not isinstance(raw, dict):
        return ""
    options = raw.get("options")
    if not isinstance(options, list):
        return ""
    rows = "".join(
        "<tr>"
        f"<td>{escape(option.get('label', ''))}</td>"
        f"<td>{escape(option.get('category', ''))}</td>"
        f"<td>{escape(option.get('intent_kind', ''))}</td>"
        f"<td>{escape(option.get('risk', ''))}</td>"
        "</tr>"
        for option in options
        if isinstance(option, dict)
    )
    leaving = "yes" if raw.get("npc_will_leave") else "no"
    return (
        "<div class='fact-card'><b>Follow-up menu</b>"
        f"<p class='muted'>NPC will leave: {escape(leaving)}</p>"
        "<table><thead><tr><th>Label</th><th>Category</th><th>Intent</th><th>Risk</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def _event_narration(raw: object) -> str:
    if not isinstance(raw, dict) or not raw.get("prose"):
        return ""
    return f"<blockquote>{escape(raw['prose'])}</blockquote>"


def _ceremony_events(raw: object) -> str:
    if not isinstance(raw, list) or not raw:
        return ""
    items = []
    for event in raw:
        if not isinstance(event, dict):
            continue
        label = f"{event.get('kind', 'event')}: {event.get('message', '')}"
        items.append(f"<li>{escape(label)}</li>")
    return f"<div class='fact-card'><b>Events</b><ul class='compact'>{''.join(items)}</ul></div>"


def _memories(raw: object) -> str:
    commits = raw if isinstance(raw, dict) else {}
    batches = commits.get("curator_batches")
    if not isinstance(batches, list) or not batches:
        return ""
    items = []
    for batch in batches:
        if not isinstance(batch, dict):
            continue
        summary = batch.get("summary")
        if summary:
            items.append(f"<li><b>Summary</b>: {escape(summary)}</li>")
        for memory in batch.get("memories", []):
            if isinstance(memory, dict):
                holder = memory.get("holder_id", "holder")
                subject = memory.get("subject_id", "subject")
                content = memory.get("content", "")
                items.append(f"<li><b>{escape(holder)} -> {escape(subject)}</b>: {escape(content)}</li>")
    return f"<div class='fact-card'><b>Memories</b><ul class='compact'>{''.join(items)}</ul></div>"


def _resort_changes(raw: object) -> str:
    commits = raw if isinstance(raw, dict) else {}
    update = commits.get("resort_update")
    background = commits.get("background_dialogues")
    parts = []
    if isinstance(update, dict):
        starts = update.get("conversation_starts") or []
        moves = update.get("npc_movements") or []
        if starts:
            parts.append(f"{len(starts)} background conversation(s) started")
        if moves:
            parts.append(f"{len(moves)} NPC movement(s)")
    if isinstance(background, list) and background:
        parts.append(f"{len(background)} background dialogue beat(s)")
    if not parts:
        return ""
    return f"<p class='muted resort-summary'>Sunset Bay life: {escape('; '.join(parts))}</p>"


def _check_row(check: dict[str, Any]) -> str:
    result = str(check.get("result") or "unknown")
    evidence = check.get("evidence")
    evidence_html = f"<p class='evidence'>{escape(evidence)}</p>" if evidence else ""
    return (
        f"<article class='check {escape(result)}'>"
        f"<span>{escape(result)}</span><b>{escape(check.get('id', 'check'))}</b>"
        f"<p>{escape(check.get('reason', ''))}</p>"
        f"{evidence_html}"
        "</article>"
    )


def _failure_summary(failed: list[dict[str, str]]) -> str:
    if not failed:
        return ""
    items = "".join(
        f"<li><b>{escape(item['turn'])}</b>: {escape(item['check'])} - {escape(item['reason'])}</li>"
        for item in failed
    )
    return f"<div class='failure-box'><b>Failure summary</b><ul>{items}</ul></div>"


def _failed_checks(scenario: GoldenScenarioResult) -> list[dict[str, str]]:
    failed = []
    for turn in scenario.turns:
        for check in turn.checks:
            if check.result == "fail":
                failed.append({"turn": turn.id, "check": check.id, "reason": check.reason})
    return failed


def _error(value: str | None) -> str:
    return f"<div class='failure-box'><b>Runtime error</b><p>{escape(value)}</p></div>" if value else ""


def _action_label(action: dict[str, Any]) -> str:
    parts = [str(action.get("kind", "action"))]
    if action.get("target_id"):
        parts.append(f"target {action['target_id']}")
    if action.get("intent_id"):
        parts.append(f"intent {action['intent_id']}")
    if action.get("option_index") is not None:
        parts.append(f"option {action['option_index']}")
    return " | ".join(parts)


def _turn_status(turn: GoldenTurnResult) -> str:
    results = [check.result for check in turn.checks]
    if "fail" in results:
        return "fail"
    if "cannot_determine" in results:
        return "cannot_determine"
    return "pass"


def _metric(label: str, value: object, status: str = "") -> str:
    return f"<div class='metric {escape(status)}'><span>{escape(label)}</span><b>{escape(value)}</b></div>"


def _badge(status: str) -> str:
    return f"<span class='badge {escape(status)}'>{escape(status.replace('_', ' '))}</span>"


def _yes_no(value: object) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "n/a"
