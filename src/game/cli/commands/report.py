"""Static HTML report generation."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from src.game.agents.contextual_options import ContextualOptionsAgent
from src.game.agents.heartbreaker_voice import OpenAIHeartbreakerVoice
from src.game.cli.commands.report_compare import compare_cmd
from src.game.cli.commands.review import review_notes_for_trace
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.bookmarks import bookmarks_for_turn
from src.game.engine.compatibility import revealed_preferences
from src.game.engine.couples import couple_strength, player_couple
from src.game.engine.flush_of_hearts import locations_for_resort
from src.game.engine.turn import run_turn
from src.game.eval.playthrough import evaluate_trace
from src.game.reporting.balance import run_balance
from src.game.reporting.eval_dashboard import playthrough_eval_page
from src.game.reporting.html import index_page, session_page, session_page_minimal, table_page
from src.game.reporting.packet_text import infer_llm_mode, llm_mode_note, notes, repro
from src.game.state.models import GameState, Location, PlayerStats, new_game
from src.game.state.rng import SeededRng
from src.game.state.snapshot import state_hash, state_hash_payload


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the report command group."""
    parser = subparsers.add_parser("report", help="generate static review reports")
    nested = parser.add_subparsers(dest="report_cmd", required=True)

    session = nested.add_parser("session", help="render one trace JSON file")
    session.add_argument("trace_path")
    session.add_argument("--out", required=True)
    session.add_argument("--minimal", action="store_true")
    session.set_defaults(func=session_cmd)

    from_trace = nested.add_parser("from-trace", help="render one recorded playthrough trace")
    from_trace.add_argument("trace_path")
    from_trace.add_argument("--out", required=True)
    from_trace.add_argument("--minimal", action="store_true")
    from_trace.set_defaults(func=session_cmd)

    balance = nested.add_parser("balance", help="render balance simulation")
    balance.add_argument("--seeds", type=int, default=1000)
    balance.add_argument("--out", required=True)
    balance.set_defaults(func=balance_cmd)

    packet = nested.add_parser("packet", help="build the full review packet")
    packet.add_argument("--trace", required=True)
    packet.add_argument("--out", default="review-packet")
    packet.add_argument("--minimal", action="store_true")
    packet.set_defaults(func=packet_cmd)

    eval_dashboard = nested.add_parser("eval-dashboard", help="render playthrough eval dashboard")
    eval_dashboard.add_argument("trace_path")
    eval_dashboard.add_argument("--out", required=True)
    eval_dashboard.set_defaults(func=eval_dashboard_cmd)

    compare = nested.add_parser("compare", help="compare two checkpoint branches")
    compare.add_argument("--checkpoint", required=True)
    compare.add_argument("--trace-a", required=True)
    compare.add_argument("--trace-b", required=True)
    compare.add_argument("--out", required=True)
    compare.set_defaults(func=compare_cmd)

    preview_f2 = nested.add_parser("preview-f2", help="build the Phase F2 voice preview")
    preview_f2.add_argument("--out", default="review-packet-preview/session-phaseF2.html")
    preview_f2.set_defaults(func=preview_f2_cmd)


def session_cmd(args: argparse.Namespace) -> int:
    """Render one existing trace file."""
    records, final_state, _final_hash, llm_mode, mode, persona = _load_recording(Path(args.trace_path))
    preface = _final_state_summary(final_state, llm_mode, mode, persona) if final_state is not None else ""
    minimal = getattr(args, "minimal", False)
    if minimal:
        html = session_page_minimal(Path(args.trace_path).stem, records, preface=preface)
    else:
        html = session_page(
            Path(args.trace_path).stem,
            records,
            preface=preface,
            final_state=final_state,
        )
    Path(args.out).write_text(html, encoding="utf-8")
    return 0


def balance_cmd(args: argparse.Namespace) -> int:
    """Render balance reports."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    outcomes, actions = run_balance(args.seeds, Path("tests/scenarios/fixtures/day6-full-run.yaml"))
    _write_balance_pages(out, outcomes, actions)
    return 0


def packet_cmd(args: argparse.Namespace) -> int:
    """Build a single-session review packet from a recorded trace."""
    trace_path = Path(args.trace)
    records, final_state, final_hash, llm_mode, mode, persona = _load_recording(trace_path)
    if final_state is None:
        raise ValueError("packet requires a recorded trace package with final_state")
    out = Path(args.out)
    _clean_packet_output(out)
    (out / "artifacts").mkdir(parents=True, exist_ok=True)
    report = evaluate_trace(
        {
            "records": records,
            "final_state": final_state,
            "final_hash": final_hash,
            "mode": mode,
            "persona": persona,
        },
        trace_path=str(trace_path),
    )
    (out / "session.html").write_text(
        session_page(
            "Recorded Playthrough",
            records,
            preface=_final_state_summary(final_state, llm_mode, mode, persona),
            reviewer_notes=review_notes_for_trace(trace_path),
            final_state=final_state,
        ),
        encoding="utf-8",
    )
    (out / "playthrough-eval.html").write_text(
        playthrough_eval_page(report),
        encoding="utf-8",
    )
    (out / "artifacts" / "session.json").write_text(
        json.dumps(final_state, indent=2),
        encoding="utf-8",
    )
    (out / "artifacts" / "session-trace.json").write_text(
        json.dumps(records, indent=2),
        encoding="utf-8",
    )
    (out / "notes.md").write_text(notes(records, final_hash, llm_mode), encoding="utf-8")
    (out / "how-to-reproduce.md").write_text(repro(trace_path, out), encoding="utf-8")
    links = [
        ("Recorded playthrough", "session.html"),
        ("Playthrough eval dashboard", "playthrough-eval.html"),
        ("Final state JSON", "artifacts/session.json"),
        ("Trace JSON", "artifacts/session-trace.json"),
        ("Notes", "notes.md"),
        ("How to reproduce", "how-to-reproduce.md"),
    ]
    (out / "index.html").write_text(index_page(links), encoding="utf-8")
    return 0


def eval_dashboard_cmd(args: argparse.Namespace) -> int:
    """Render only the playthrough eval dashboard for one trace."""
    records, final_state, final_hash, _llm_mode, mode, persona = _load_recording(Path(args.trace_path))
    report = evaluate_trace(
        {
            "records": records,
            "final_state": final_state,
            "final_hash": final_hash,
            "mode": mode,
            "persona": persona,
        },
        trace_path=args.trace_path,
    )
    Path(args.out).write_text(playthrough_eval_page(report), encoding="utf-8")
    return 0


def preview_f2_cmd(args: argparse.Namespace) -> int:
    """Build the mandatory Phase F2 single-exchange voice preview."""
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    state = new_game(42, player_stats=PlayerStats(charm=3, banter=3, eq=3, spark=3, loyalty=3))
    for heartbreaker in state.heartbreakers:
        heartbreaker.location_id = Location.POOL
    rng = SeededRng(42)
    heartbreaker_voice = OpenAIHeartbreakerVoice().generate
    contextual_options = ContextualOptionsAgent().generate
    actions = [
        ("chloe", "friendly_ask_feelings", 10),
        ("chloe", "friendly_chat_resort", 10),
        ("chloe", "friendly_compliment_personality", 10),
        ("maya", "flirty_compliment_looks", 20),
        ("maya", "flirty_playful_teasing", 20),
        ("maya", "flirty_intimate_eye_contact", 30),
        ("liam", "deep_ask_life", 40),
        ("liam", "deep_share_feelings", 40),
        ("chloe", "banter_tell_joke", 10),
        ("chloe", "banter_playful_roast", 10),
    ]
    records: list[dict[str, Any]] = []
    for target_id, intent_id, affection in actions:
        _set_preview_target(state, target_id, affection)
        action = PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id=target_id,
            intent_id=intent_id,
        )
        input_hash = state_hash(state_hash_payload(state))
        turn = run_turn(
            state,
            action,
            rng,
            heartbreaker_voice=heartbreaker_voice,
            contextual_options=contextual_options,
        )
        state = turn.state
        records.append(_record_from_turn(input_hash, action, turn))

    preface = (
        "<p><b>About this preview.</b> This page demonstrates the Heartbreaker Voice agent across "
        "all four conversation categories. Affection is pre-warmed before each turn to the intent's "
        "unlock threshold so every tier is visible — a real session evolves these values gradually. "
        "Player stats are deliberately set to the minimum (3 across all five stats) so misses are "
        "plausible. Read each turn as a voice-quality sample, not as a continuous narrative.</p>"
    )
    out.write_text(
        session_page("Phase F2 Voice Preview", records, preface=preface),
        encoding="utf-8",
    )
    print(out)
    return 0


def _record_from_turn(input_hash: str, action: PlayerAction, turn: object) -> dict[str, Any]:
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        raise TypeError("turn must be TurnResult")
    state = turn.state
    return {
        "turn": state.turn_index,
        "day": state.day,
        "phase": state.phase.value,
        "resort": state.resort.value,
        "location": state.location_id.value,
        "player_public_perception": state.player.public_perception,
        "visible_state": _visible_state(state),
        "resort_snapshot": _resort_snapshot(state),
        "couple_strength": _player_couple_strength(state),
        "private_suite": state.private_suite.model_dump(mode="json"),
        "flush_of_hearts": (
            None
            if state.flush_of_hearts_state is None
            else state.flush_of_hearts_state.model_dump(mode="json")
        ),
        "input_hash": input_hash,
        "action": action.model_dump(mode="json"),
        "mechanical_result": turn.mechanical_result.model_dump(mode="json"),
        "exchange": None if turn.exchange is None else turn.exchange.model_dump(mode="json"),
        "event_narration": (
            None
            if turn.event_narration is None
            else turn.event_narration.model_dump(mode="json")
        ),
        "follow_up_menu": (
            None if turn.follow_up_menu is None else turn.follow_up_menu.model_dump(mode="json")
        ),
        "ceremony_events": [event.model_dump(mode="json") for event in turn.ceremony_events],
        "audience_snapshot": (
            None if turn.audience_snapshot is None else turn.audience_snapshot.model_dump(mode="json")
        ),
        "challenge": None if state.pending_challenge is None else state.pending_challenge.model_dump(mode="json"),
        "producer_text": None if state.pending_text is None else state.pending_text.model_dump(mode="json"),
        "pending_gather": None if state.pending_gather is None else state.pending_gather.model_dump(mode="json"),
        "group_date": None if state.pending_group_date is None else state.pending_group_date.model_dump(mode="json"),
        "daily_recaps": [recap.model_dump(mode="json") for recap in state.daily_recaps],
        "revealed_preferences": {
            heartbreaker.id: revealed
            for heartbreaker in state.heartbreakers
            if (revealed := revealed_preferences(heartbreaker))
        },
        "agent_commits": turn.agent_commits.model_dump(mode="json"),
        "agent_traces": [trace.model_dump(mode="json") for trace in turn.agent_traces],
        "bookmarks": [bookmark.model_dump(mode="json") for bookmark in bookmarks_for_turn(turn)],
        "output_hash": turn.state_hash,
    }


def _set_preview_target(state: GameState, target_id: str, affection: int) -> None:
    for heartbreaker in state.heartbreakers:
        if heartbreaker.id == target_id:
            heartbreaker.location_id = state.location_id
            heartbreaker.relationship.affection = affection
            return
    raise ValueError(f"preview target not found: {target_id}")


def _visible_state(state: GameState) -> str:
    parts = []
    for heartbreaker in state.heartbreakers:
        if heartbreaker.location_id == state.location_id and not heartbreaker.eliminated:
            rel = heartbreaker.relationship
            parts.append(
                f"{heartbreaker.name}: affection {rel.affection}, chemistry {rel.chemistry}, trust {rel.trust}"
            )
    return "; ".join(parts) if parts else "No visible heartbreakers."


def _player_couple_strength(state: GameState) -> int | None:
    couple = player_couple(state)
    return None if couple is None else couple_strength(state, couple)


def _resort_snapshot(state: GameState) -> dict[str, list[str]]:
    snapshot: dict[str, list[str]] = {}
    for location in locations_for_resort(state.resort):
        occupants = ["you"] if location is state.location_id else []
        occupants.extend(
            heartbreaker.name
            for heartbreaker in state.heartbreakers
            if heartbreaker.location_id is location and not heartbreaker.eliminated
        )
        snapshot[location.value] = occupants
    return snapshot


def _write_balance_pages(out: Path, outcomes: object, actions: object) -> None:
    out.mkdir(parents=True, exist_ok=True)
    outcome_rows = [[str(key), str(value)] for key, value in sorted(outcomes.items())]
    action_rows = [[str(key), str(value)] for key, value in sorted(actions.items())]
    (out / "distribution.html").write_text(
        table_page("Balance Distribution", ["Outcome", "Count"], outcome_rows),
        encoding="utf-8",
    )
    (out / "action-coverage.html").write_text(
        table_page("Action Coverage", ["Action", "Count"], action_rows),
        encoding="utf-8",
    )


def _load_recording(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None, str | None, str, str, str | None]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw, None, None, infer_llm_mode(raw), "manual", None
    if not isinstance(raw, dict):
        raise ValueError(f"recording must be a JSON object or list: {path}")
    records = raw.get("records")
    if not isinstance(records, list):
        raise ValueError(f"recording is missing records list: {path}")
    final_state = raw.get("final_state")
    if final_state is not None and not isinstance(final_state, dict):
        raise ValueError(f"recording final_state must be an object: {path}")
    final_hash = raw.get("final_hash")
    if final_hash is not None and not isinstance(final_hash, str):
        raise ValueError(f"recording final_hash must be a string: {path}")
    llm_mode = raw.get("llm_mode")
    if not isinstance(llm_mode, str):
        llm_mode = infer_llm_mode(records)
    mode = raw.get("mode")
    if not isinstance(mode, str):
        mode = "manual"
    persona = raw.get("persona")
    if not isinstance(persona, str):
        persona = None
    return records, final_state, final_hash, llm_mode, mode, persona


def _clean_packet_output(out: Path) -> None:
    for directory in ("artifacts", "sessions", "balance", "narration-quality"):
        shutil.rmtree(out / directory, ignore_errors=True)
    for file_name in ("index.html", "session.html", "playthrough-eval.html", "notes.md", "how-to-reproduce.md"):
        (out / file_name).unlink(missing_ok=True)


def _final_state_summary(final_state: dict[str, Any], llm_mode: str, mode: str, persona: str | None) -> str:
    player = final_state.get("player")
    heartbreakers = final_state.get("heartbreakers")
    memory_lines: list[str] = []
    if isinstance(player, dict):
        memories = player.get("memories")
        if isinstance(memories, list):
            memory_lines.append(f"<li>Player memories: {len(memories)}</li>")
        outcome = final_state.get("outcome")
        if isinstance(outcome, str):
            memory_lines.append(f"<li>Final outcome: {outcome}</li>")
    if isinstance(heartbreakers, list):
        for heartbreaker in heartbreakers:
            if not isinstance(heartbreaker, dict):
                continue
            memories = heartbreaker.get("memories")
            name = heartbreaker.get("name", heartbreaker.get("id", "heartbreaker"))
            if isinstance(memories, list):
                memory_lines.append(f"<li>{name} memories: {len(memories)}</li>")
    return (
        "<p><b>Recorded playthrough.</b> This report is rendered from a trace package; "
        "agent commits are replayable and no new LLM calls are needed to inspect it.</p>"
        f"<p><b>LLM mode:</b> {llm_mode}. "
        f"{llm_mode_note(llm_mode)}</p>"
        f"<p><b>Trace mode:</b> {mode}{f' - persona: {persona}' if persona else ''}.</p>"
        f"<ul>{''.join(memory_lines)}</ul>"
    )
