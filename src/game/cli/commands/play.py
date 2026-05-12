"""Interactive play command."""

from __future__ import annotations

import argparse
import json
import sys
from itertools import groupby
from pathlib import Path
from typing import Any

from src.game.agents.background_dialogue import OpenAIBackgroundDialogue
from src.game.agents.contextual_options import ContextualOptionsAgent
from src.game.agents.conversation_curator import OpenAIConversationCurator
from src.game.agents.event_narrator import OpenAIEventNarrator
from src.game.agents.islander_voice import OpenAIIslanderVoice
from src.game.agents.villa_orchestrator import OpenAIVillaOrchestrator
from src.game.engine.actions import ActionKind, ActionSpec, PlayerAction, available_actions
from src.game.engine.intents import IntentCategory, available_intents_for
from src.game.engine.recorded_agents import RecordedAgents
from src.game.engine.turn import TurnResult, run_turn
from src.game.state.models import GameState, new_game
from src.game.state.rng import SeededRng
from src.game.state.snapshot import state_hash, state_hash_payload


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the play command."""
    parser = subparsers.add_parser("play", help="start an interactive CLI game")
    parser.add_argument("--snapshot", help="snapshot to load")
    parser.add_argument("--seed", type=int, help="seed for a new run")
    parser.add_argument("--mock-llm", action="store_true", help="use deterministic mock narration")
    parser.add_argument("--trace", action="store_true", help="write turn traces")
    parser.add_argument("--record", help="record this live session to a trace package")
    parser.add_argument("--replay", help="replay a recorded trace package without LLM calls")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    if args.snapshot:
        print("play --snapshot is not implemented yet", file=sys.stderr)
        return 2
    if args.record and args.replay:
        print("choose either --record or --replay, not both", file=sys.stderr)
        return 2
    if args.replay:
        return _replay_recording(Path(args.replay))

    seed = 1 if args.seed is None else args.seed
    state = new_game(seed)
    rng = SeededRng(seed)
    islander_voice = None if args.mock_llm else OpenAIIslanderVoice().generate
    contextual_options = None if args.mock_llm else ContextualOptionsAgent().generate
    event_narrator = None if args.mock_llm else OpenAIEventNarrator().narrate
    conversation_curator = None if args.mock_llm else OpenAIConversationCurator().curate
    villa_orchestrator = None if args.mock_llm else OpenAIVillaOrchestrator().decide
    background_dialogue = None if args.mock_llm else OpenAIBackgroundDialogue().generate
    record_path = None if args.record is None else Path(args.record)
    records: list[dict[str, Any]] = []
    print("Game CLI. Type a number, /state, /hash, /help, or /quit.")

    while not state.is_terminal:
        _print_state(state)
        actions = available_actions(state)
        _print_actions(actions)
        raw = input("> ").strip()
        if raw in {"/quit", "quit", "q"}:
            _write_recording(record_path, seed, state, records)
            return 0
        if raw == "/help":
            print("Commands: /state, /hash, /help, /quit. Choose actions by number.")
            continue
        if raw == "/state":
            _print_state(state, debug=True)
            continue
        if raw == "/hash":
            print(state_hash(state_hash_payload(state)))
            continue

        try:
            index = int(raw) - 1
            action = actions[index].action
        except (ValueError, IndexError):
            print("choose a listed action number or slash command")
            continue
        if action.kind is ActionKind.START_CONVERSATION and action.target_id is not None:
            action = _choose_intent(state, action.target_id)

        input_hash = state_hash(state_hash_payload(state))
        turn = run_turn(
            state,
            action,
            rng,
            islander_voice=islander_voice,
            contextual_options=contextual_options,
            event_narrator=event_narrator,
            conversation_curator=conversation_curator,
            villa_orchestrator=villa_orchestrator,
            background_dialogue=background_dialogue,
        )
        state = turn.state
        records.append(_record_from_turn(input_hash, action, turn))
        _write_recording(record_path, seed, state, records)
        _print_turn(turn)

    print("Day complete.")
    print(f"final hash: {state_hash(state_hash_payload(state))}")
    _write_recording(record_path, seed, state, records)
    return 0


def _print_state(state: GameState, *, debug: bool = False) -> None:
    print(f"\nDay {state.day} | {state.phase.value} | turn {state.turn_index}")
    print(f"Location: {state.location_id}")
    for islander in state.islanders:
        detail = f" affection={islander.relationship.affection}" if debug else ""
        print(f"- {islander.name} ({islander.archetype}){detail}")


def _print_actions(actions: list[ActionSpec]) -> None:
    if any(spec.action.kind is ActionKind.RESPOND_WITH for spec in actions):
        _print_follow_up_actions(actions)
        return
    for index, spec in enumerate(actions, start=1):
        print(f"{index}. {spec.label}")


def _print_turn(turn: TurnResult) -> None:
    result = turn.mechanical_result
    if turn.exchange is not None:
        print(f'You: "{turn.exchange.player_dialogue}"')
        print(f'{_target_name(turn)}: {turn.exchange.npc_dialogue}')
    if turn.event_narration is not None:
        print(turn.event_narration.prose)
    if turn.agent_commits.villa_update is not None:
        _print_villa_update(turn)
    if turn.follow_up_menu is not None and turn.follow_up_menu.npc_will_leave:
        print(turn.follow_up_menu.npc_exit_line)
    if result.roll is not None and result.success_chance is not None:
        outcome = "success" if result.success else "miss"
        print(f"{outcome}: rolled {result.roll} vs {result.success_chance}")
    print(f"hash: {turn.state_hash}")


def _print_villa_update(turn: TurnResult) -> None:
    update = turn.agent_commits.villa_update
    if update is None:
        return
    parts: list[str] = []
    if update.npc_movements:
        parts.append(f"{len(update.npc_movements)} move")
    if update.conversation_starts:
        parts.append(f"{len(update.conversation_starts)} start")
    if update.conversation_continues:
        parts.append(f"{len(update.conversation_continues)} continue")
    if update.conversation_ends:
        parts.append(f"{len(update.conversation_ends)} end")
    if parts:
        print(f"Villa: {', '.join(parts)}")


def _print_follow_up_actions(actions: list[ActionSpec]) -> None:
    numbered = list(enumerate(actions, start=1))
    followups = [
        (index, spec)
        for index, spec in numbered
        if spec.action.kind is ActionKind.RESPOND_WITH
    ]
    for category, category_specs in groupby(followups, key=lambda item: item[1].label.split(":", 1)[0]):
        print(f"{category}:")
        for index, spec in category_specs:
            label = spec.label.split(":", 1)[1].strip() if ":" in spec.label else spec.label
            print(f"  {index}. {label}")
    for index, spec in numbered:
        if spec.action.kind is not ActionKind.RESPOND_WITH:
            print(f"{index}. {spec.label}")


def _target_name(turn: TurnResult) -> str:
    target_id = turn.mechanical_result.action.target_id
    for islander in turn.state.islanders:
        if islander.id == target_id:
            return islander.name
    return "Islander"


def _choose_intent(state: GameState, target_id: str) -> PlayerAction:
    intents = available_intents_for(state, target_id)
    numbered: list[tuple[int, str]] = []
    index = 1
    for category in IntentCategory:
        category_intents = [intent for intent in intents if intent.category is category]
        print(f"{category.value.title()}:")
        if not category_intents:
            print("  locked")
            continue
        for intent in category_intents:
            print(f"  {index}. {intent.label} ({intent.stat_used})")
            numbered.append((index, intent.id))
            index += 1
    while True:
        raw = input("intent> ").strip()
        try:
            chosen = int(raw)
        except ValueError:
            print("choose an intent number")
            continue
        for number, intent_id in numbered:
            if number == chosen:
                return PlayerAction(
                    kind=ActionKind.START_CONVERSATION,
                    target_id=target_id,
                    intent_id=intent_id,
                )
        print("choose an intent number")


def _replay_recording(path: Path) -> int:
    package = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(package, dict):
        raise ValueError(f"recording must be a JSON object: {path}")
    seed = package.get("seed")
    records = package.get("records")
    expected_final_hash = package.get("final_hash")
    if not isinstance(seed, int) or not isinstance(records, list):
        raise ValueError("recording requires integer seed and records list")
    state = new_game(seed)
    rng = SeededRng(seed)
    agents = RecordedAgents()
    for raw_record in records:
        if not isinstance(raw_record, dict):
            raise ValueError("each recorded turn must be an object")
        agents.begin_turn(raw_record)
        action = PlayerAction.model_validate(raw_record.get("action"))
        input_hash = state_hash(state_hash_payload(state))
        if raw_record.get("input_hash") != input_hash:
            raise ValueError(
                f"input hash mismatch on recorded turn {raw_record.get('turn')}: "
                f"expected {raw_record.get('input_hash')}, got {input_hash}"
            )
        turn = run_turn(
            state,
            action,
            rng,
            islander_voice=agents.islander_voice if raw_record.get("exchange") is not None else None,
            contextual_options=(
                agents.contextual_options if raw_record.get("follow_up_menu") is not None else None
            ),
            event_narrator=(
                agents.event_narrator if raw_record.get("event_narration") is not None else None
            ),
            conversation_curator=agents.conversation_curator,
            villa_orchestrator=agents.villa_orchestrator,
            background_dialogue=agents.background_dialogue,
        )
        state = turn.state
        if turn.state_hash != raw_record.get("output_hash"):
            raise ValueError(
                f"output hash mismatch on recorded turn {raw_record.get('turn')}: "
                f"expected {raw_record.get('output_hash')}, got {turn.state_hash}"
            )
    final_hash = state_hash(state_hash_payload(state))
    if isinstance(expected_final_hash, str) and expected_final_hash != final_hash:
        raise ValueError(f"final hash mismatch: expected {expected_final_hash}, got {final_hash}")
    print(f"replayed {len(records)} turn(s)")
    print(f"final hash: {final_hash}")
    return 0


def _record_from_turn(input_hash: str, action: PlayerAction, turn: TurnResult) -> dict[str, Any]:
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
        "ceremony_events": [event.model_dump(mode="json") for event in turn.ceremony_events],
        "agent_commits": turn.agent_commits.model_dump(mode="json"),
        "output_hash": turn.state_hash,
    }


def _visible_state(state: GameState) -> str:
    parts = []
    for islander in state.islanders:
        if islander.location_id == state.location_id and not islander.eliminated:
            rel = islander.relationship
            parts.append(
                f"{islander.name}: affection {rel.affection}, chemistry {rel.chemistry}, "
                f"trust {rel.trust}, friendship {rel.friendship}"
            )
    return "; ".join(parts) if parts else "No visible islanders."


def _write_recording(
    path: Path | None,
    seed: int,
    state: GameState,
    records: list[dict[str, Any]],
) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    package = {
        "seed": seed,
        "final_hash": state_hash(state_hash_payload(state)),
        "records": records,
        "final_state": state.model_dump(mode="json"),
    }
    path.write_text(json.dumps(package, indent=2), encoding="utf-8")
