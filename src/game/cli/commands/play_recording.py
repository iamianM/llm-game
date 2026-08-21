"""Recording helpers for CLI play sessions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.game.engine.actions import PlayerAction
from src.game.engine.bookmarks import bookmarks_for_turn
from src.game.engine.compatibility import revealed_preferences
from src.game.engine.couples import couple_strength, player_couple
from src.game.engine.flush_of_hearts import locations_for_resort
from src.game.engine.turn import TurnResult
from src.game.presentation.daily_recap import project_daily_recap
from src.game.state.models import GameState
from src.game.state.snapshot import state_hash, state_hash_payload
from src.game.state.trace import TraceMode


def record_from_turn(input_hash: str, action: PlayerAction, turn: TurnResult) -> dict[str, Any]:
    """Serialize one turn for replay and report generation."""
    state = turn.state
    return {
        "turn": state.turn_index,
        "day": state.day,
        "phase": state.phase.value,
        "resort": state.resort.value,
        "location": state.location_id.value,
        "player_public_perception": state.player.public_perception,
        "phase_clock": state.phase_clock.model_dump(mode="json"),
        "time_cost": turn.time_cost,
        "auto_advance": turn.auto_advance,
        "arrival_rolls": [roll.model_dump(mode="json") for roll in turn.arrival_rolls],
        "visible_state": _visible_state(state),
        "resort_snapshot": _resort_snapshot(state),
        "couple_strength": _player_couple_strength(state),
        "private_suite": state.private_suite.model_dump(mode="json"),
        "flush_of_hearts": None if state.flush_of_hearts_state is None else state.flush_of_hearts_state.model_dump(mode="json"),
        "input_hash": input_hash,
        "action": action.model_dump(mode="json"),
        "mechanical_result": turn.mechanical_result.model_dump(mode="json"),
        "exchange": None if turn.exchange is None else turn.exchange.model_dump(mode="json"),
        "event_narration": None if turn.event_narration is None else turn.event_narration.model_dump(mode="json"),
        "follow_up_menu": None if turn.follow_up_menu is None else turn.follow_up_menu.model_dump(mode="json"),
        "ceremony_events": [event.model_dump(mode="json") for event in turn.ceremony_events],
        "audience_snapshot": None if turn.audience_snapshot is None else turn.audience_snapshot.model_dump(mode="json"),
        "challenge": None if state.pending_challenge is None else state.pending_challenge.model_dump(mode="json"),
        "producer_text": None if state.pending_text is None else state.pending_text.model_dump(mode="json"),
        "pending_gather": None if state.pending_gather is None else state.pending_gather.model_dump(mode="json"),
        "group_date": None if state.pending_group_date is None else state.pending_group_date.model_dump(mode="json"),
        "daily_recaps": [
            project_daily_recap(state, recap).model_dump(mode="json")
            for recap in state.daily_recaps
        ],
        "revealed_preferences": {
            heartbreaker.id: revealed
            for heartbreaker in state.heartbreakers
            if (revealed := revealed_preferences(heartbreaker))
        },
        "agent_commits": turn.agent_commits.model_dump(mode="json"),
        "conversation_closures": [
            closure.model_dump(mode="json") for closure in turn.conversation_closures
        ],
        "agent_traces": [trace.model_dump(mode="json") for trace in turn.agent_traces],
        "bookmarks": [bookmark.model_dump(mode="json") for bookmark in bookmarks_for_turn(turn)],
        "output_hash": turn.state_hash,
    }


def write_recording(
    path: Path | None,
    seed: int,
    state: GameState,
    records: list[dict[str, Any]],
    *,
    llm_mode: str,
    mode: TraceMode,
    persona: str,
) -> None:
    """Write a complete trace package after every turn."""
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    package = {
        "seed": seed,
        "mode": mode.value,
        "persona": persona,
        "llm_mode": llm_mode,
        "character_creation": (
            None if state.character_creation is None else state.character_creation.model_dump(mode="json")
        ),
        "final_hash": state_hash(state_hash_payload(state)),
        "records": records,
        "final_state": state.model_dump(mode="json"),
    }
    path.write_text(json.dumps(package, indent=2), encoding="utf-8")


def llm_mode(args: argparse.Namespace) -> str:
    return "mock" if args.mock_llm else "real"


def trace_mode(args: argparse.Namespace) -> TraceMode:
    if args.mock_llm:
        return TraceMode.MOCKED
    return TraceMode.MANUAL


def _visible_state(state: GameState) -> str:
    parts = []
    for heartbreaker in state.heartbreakers:
        if heartbreaker.location_id == state.location_id and not heartbreaker.eliminated:
            rel = heartbreaker.relationship
            parts.append(
                f"{heartbreaker.name}: affection {rel.affection}, chemistry {rel.chemistry}, "
                f"trust {rel.trust}, friendship {rel.friendship}"
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
