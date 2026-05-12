"""Static HTML report generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.game.agents.contextual_options import ContextualOptionsAgent, mock_follow_up_menu
from src.game.agents.event_narrator import OpenAIEventNarrator
from src.game.agents.islander_voice import Exchange, OpenAIIslanderVoice
from src.game.engine.actions import ActionKind, PlayerAction
from src.game.engine.rules import MechanicalResult
from src.game.engine.scenario import load_action_script
from src.game.engine.turn import run_turn
from src.game.reporting.balance import run_balance
from src.game.reporting.html import index_page, session_page, table_page
from src.game.state.models import FollowUpMenu, GameState, Location, PlayerStats, new_game
from src.game.state.rng import SeededRng
from src.game.state.snapshot import state_hash, state_hash_payload


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the report command group."""
    parser = subparsers.add_parser("report", help="generate static review reports")
    nested = parser.add_subparsers(dest="report_cmd", required=True)

    session = nested.add_parser("session", help="render one trace JSON file")
    session.add_argument("trace_path")
    session.add_argument("--out", required=True)
    session.set_defaults(func=session_cmd)

    balance = nested.add_parser("balance", help="render balance simulation")
    balance.add_argument("--seeds", type=int, default=1000)
    balance.add_argument("--out", required=True)
    balance.set_defaults(func=balance_cmd)

    packet = nested.add_parser("packet", help="build the full review packet")
    packet.add_argument("--out", required=True)
    packet.add_argument("--mock-llm", action="store_true")
    packet.set_defaults(func=packet_cmd)

    preview_f2 = nested.add_parser("preview-f2", help="build the Phase F2 voice preview")
    preview_f2.add_argument("--out", default="review-packet-preview/session-phaseF2.html")
    preview_f2.set_defaults(func=preview_f2_cmd)


def session_cmd(args: argparse.Namespace) -> int:
    """Render one existing trace file."""
    records = json.loads(Path(args.trace_path).read_text(encoding="utf-8"))
    Path(args.out).write_text(session_page(Path(args.trace_path).stem, records), encoding="utf-8")
    return 0


def balance_cmd(args: argparse.Namespace) -> int:
    """Render balance reports."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    outcomes, actions = run_balance(args.seeds, Path("tests/scenarios/fixtures/day6-full-run.yaml"))
    _write_balance_pages(out, outcomes, actions)
    return 0


def packet_cmd(args: argparse.Namespace) -> int:
    """Build the full self-contained review packet."""
    out = Path(args.out)
    (out / "sessions").mkdir(parents=True, exist_ok=True)
    (out / "balance").mkdir(parents=True, exist_ok=True)
    (out / "narration-quality").mkdir(parents=True, exist_ok=True)
    (out / "artifacts").mkdir(parents=True, exist_ok=True)

    policies = [
        ("session-01-loyal", Path("scripts/fixtures/policy-loyal.yaml")),
        ("session-02-chaotic", Path("scripts/fixtures/policy-chaotic.yaml")),
        ("session-03-strategic", Path("scripts/fixtures/policy-strategic.yaml")),
    ]
    all_records: list[dict[str, Any]] = []
    for name, path in policies:
        records, final_state = _run_session(path, use_llm=not args.mock_llm)
        all_records.extend(records)
        (out / "sessions" / f"{name}.html").write_text(
            session_page(name, records),
            encoding="utf-8",
        )
        (out / "artifacts" / f"{name}.json").write_text(
            json.dumps(final_state.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        (out / "artifacts" / f"{name}-trace.json").write_text(
            json.dumps(records, indent=2),
            encoding="utf-8",
        )

    outcomes, actions = run_balance(1000, Path("tests/scenarios/fixtures/day6-full-run.yaml"))
    _write_balance_pages(out / "balance", outcomes, actions)
    sample = [record for record in all_records if record["exchange"] is not None][:20]
    (out / "narration-quality" / "sample-20-turns.html").write_text(
        session_page("Narration Sample", sample),
        encoding="utf-8",
    )
    (out / "narration-quality" / "flagged.md").write_text(
        _flagged_turns(all_records),
        encoding="utf-8",
    )
    (out / "notes.md").write_text(_notes(), encoding="utf-8")
    (out / "how-to-reproduce.md").write_text(_repro(), encoding="utf-8")
    links = [
        ("Loyal session", "sessions/session-01-loyal.html"),
        ("Chaotic session", "sessions/session-02-chaotic.html"),
        ("Strategic session", "sessions/session-03-strategic.html"),
        ("Balance distribution", "balance/distribution.html"),
        ("Action coverage", "balance/action-coverage.html"),
        ("Narration sample", "narration-quality/sample-20-turns.html"),
        ("Flagged turns", "narration-quality/flagged.md"),
        ("Notes", "notes.md"),
        ("How to reproduce", "how-to-reproduce.md"),
    ]
    (out / "index.html").write_text(index_page(links), encoding="utf-8")
    return 0


def preview_f2_cmd(args: argparse.Namespace) -> int:
    """Build the mandatory Phase F2 single-exchange voice preview."""
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    state = new_game(42, player_stats=PlayerStats(charm=3, banter=3, eq=3, graft=3, loyalty=3))
    for islander in state.islanders:
        islander.location_id = Location.POOL
    rng = SeededRng(42)
    islander_voice = OpenAIIslanderVoice().generate
    contextual_options = ContextualOptionsAgent().generate
    actions = [
        ("chloe", "friendly_ask_feelings", 10),
        ("chloe", "friendly_chat_villa", 10),
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
            islander_voice=islander_voice,
            contextual_options=contextual_options,
        )
        state = turn.state
        records.append(_record_from_turn(input_hash, action, turn))

    preface = (
        "<p><b>About this preview.</b> This page demonstrates the Islander Voice agent across "
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


def _run_session(path: Path, *, use_llm: bool) -> tuple[list[dict[str, Any]], GameState]:
    script = load_action_script(path)
    state = new_game(script.seed, player_stats=script.player_stats)
    rng = SeededRng(script.seed)
    islander_voice = OpenAIIslanderVoice().generate if use_llm else None
    contextual_options = (
        ContextualOptionsAgent().generate if use_llm else _scripted_contextual_options(script.actions)
    )
    event_narrator = OpenAIEventNarrator().narrate if use_llm else None
    records: list[dict[str, Any]] = []
    for action in script.actions:
        input_hash = state_hash(state_hash_payload(state))
        turn = run_turn(
            state,
            action,
            rng,
            islander_voice=islander_voice,
            contextual_options=contextual_options,
            event_narrator=event_narrator,
        )
        state = turn.state
        records.append(_record_from_turn(input_hash, action, turn))
    return records, state


def _scripted_contextual_options(actions: list[PlayerAction]):
    planned = _planned_follow_up_intents(actions)
    index = 0

    def contextual_options(
        _state: GameState,
        _result: MechanicalResult,
        _exchange: Exchange,
        _probability: int,
    ) -> FollowUpMenu:
        nonlocal index
        intent_kind = planned[index] if index < len(planned) else None
        index += 1
        if intent_kind is None:
            return mock_follow_up_menu(npc_will_leave=True)
        return mock_follow_up_menu(intent_kind=intent_kind)

    return contextual_options


def _planned_follow_up_intents(actions: list[PlayerAction]) -> list[str | None]:
    planned: list[str | None] = []
    for index, action in enumerate(actions):
        if action.kind not in {ActionKind.START_CONVERSATION, ActionKind.RESPOND_WITH}:
            continue
        next_action = actions[index + 1] if index + 1 < len(actions) else None
        if next_action is not None and next_action.kind is ActionKind.RESPOND_WITH:
            planned.append(next_action.intent_id or "joke_back")
        elif next_action is not None and next_action.kind is ActionKind.END_CONVERSATION:
            planned.append("end_softly")
        else:
            planned.append(None)
    return planned


def _record_from_turn(input_hash: str, action: PlayerAction, turn: object) -> dict[str, Any]:
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        raise TypeError("turn must be TurnResult")
    state = turn.state
    return {
        "turn": state.turn_index,
        "day": state.day,
        "phase": state.phase.value,
        "location": state.location_id.value,
        "visible_state": _visible_state(state),
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
        "output_hash": turn.state_hash,
    }


def _set_preview_target(state: GameState, target_id: str, affection: int) -> None:
    for islander in state.islanders:
        if islander.id == target_id:
            islander.location_id = state.location_id
            islander.relationship.affection = affection
            return
    raise ValueError(f"preview target not found: {target_id}")


def _visible_state(state: GameState) -> str:
    parts = []
    for islander in state.islanders:
        if islander.location_id == state.location_id and not islander.eliminated:
            rel = islander.relationship
            parts.append(
                f"{islander.name}: affection {rel.affection}, chemistry {rel.chemistry}, trust {rel.trust}"
            )
    return "; ".join(parts) if parts else "No visible islanders."


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


def _flagged_turns(records: list[dict[str, Any]]) -> str:
    flags: list[str] = []
    for record in records:
        exchange = record.get("exchange")
        result = record.get("mechanical_result")
        if not isinstance(exchange, dict) or not isinstance(result, dict):
            continue
        if result.get("success") is False and exchange.get("npc_tone") == "warm":
            flags.append(
                f"- Turn {record['turn']} ({record['day']}/{record['phase']}): miss with warm tone."
            )
    if not flags:
        return "# Flagged Turns\n\nNo automatic flags in this packet.\n"
    return "# Flagged Turns\n\n" + "\n".join(flags) + "\n"


def _notes() -> str:
    return """# Notes

## What I noticed

The F3 loop now shows multi-exchange conversations: each session opens with
several one-on-one chats, generated player lines, Islander responses, and
contextual follow-up menus. Ceremony and bombshell events are visible in the
turn cards instead of being hidden in final state.

## What felt good

The report makes every roll, delta, hash, exchange, follow-up menu, and event
callout inspectable in one pass. The policy scripts now spend meaningful time in
conversation before the day clock starts moving.

## What felt off

Follow-up responses are mechanically neutral in this slice, so the conversation
feels alive in prose before it fully changes relationship state. The next
game-feel pass should decide which contextual follow-up tags produce real deltas.

## Open questions

- Which contextual follow-up tags should affect affection, trust, chemistry, or friendship?
- Should the report policies push harder into flirty/deep content once more unlock paths exist?
- Should recouplings give the player an explicit choice in the CLI?
"""


def _repro() -> str:
    return """# How To Reproduce

```bash
uv run python -m src.game.cli report packet --out review-packet/
uv run python -m src.game.cli report packet --out review-packet/ --mock-llm
uv run python -m src.game.cli replay --actions tests/scenarios/fixtures/day6-full-run.yaml --mock-llm
uv run python -m src.game.cli verify --all
```
"""
