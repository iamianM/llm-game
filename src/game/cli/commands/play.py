"""Interactive play command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.game.agents.background_dialogue import OpenAIBackgroundDialogue
from src.game.agents.contextual_options import ContextualOptionsAgent
from src.game.agents.conversation_curator import OpenAIConversationCurator
from src.game.agents.event_narrator import OpenAIEventNarrator
from src.game.agents.islander_voice import OpenAIIslanderVoice
from src.game.agents.villa_orchestrator import OpenAIVillaOrchestrator
from src.game.cli.commands.play_render import (
    print_actions as _print_actions,
)
from src.game.cli.commands.play_render import (
    print_character_card as _print_character_card,
)
from src.game.cli.commands.play_render import (
    print_state as _print_state,
)
from src.game.cli.commands.play_render import (
    print_turn as _print_turn,
)
from src.game.cli.commands.play_render import (
    print_villa_update as _print_villa_update,
)
from src.game.engine.actions import ActionKind, PlayerAction, available_actions
from src.game.engine.character_creation import (
    DEFAULT_ARCHETYPE_STATS,
    PLAYER_ARCHETYPES,
    create_character,
)
from src.game.engine.intents import IntentCategory, available_intents_for
from src.game.engine.recorded_agents import RecordedAgents
from src.game.engine.turn import TurnResult, run_turn
from src.game.state.models import CharacterCreation, GameState, Location, PlayerStats, new_game
from src.game.state.rng import SeededRng
from src.game.state.snapshot import state_hash, state_hash_payload


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the play command."""
    parser = subparsers.add_parser("play", help="start an interactive CLI game")
    parser.add_argument("--seed", type=int, help="seed for a new run")
    parser.add_argument("--mock-llm", action="store_true", help="use deterministic mock narration")
    parser.add_argument("--trace", action="store_true", help="write turn traces")
    parser.add_argument("--record", help="record this live session to a trace package")
    parser.add_argument("--replay", help="replay a recorded trace package without LLM calls")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    if args.record and args.replay:
        print("choose either --record or --replay, not both")
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
    _run_character_creation_flow(state)
    print("Game CLI. Type a number, /state, /hash, /help, or /quit.")

    while not state.is_terminal:
        _print_state(state)
        actions = available_actions(state)
        _print_actions(actions)
        raw = input("> ").strip()
        if raw in {"/quit", "quit", "q"}:
            _write_recording(record_path, seed, state, records, llm_mode=_llm_mode(args))
            return 0
        if raw == "/help":
            print(
                "Commands: /state, /hash, /help, /quit. Choose actions by number. "
                "Wheel exit options close gracefully; Walk away is curt."
            )
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
        _write_recording(record_path, seed, state, records, llm_mode=_llm_mode(args))
        _print_turn(turn)

    print("Day complete.")
    print(f"final hash: {state_hash(state_hash_payload(state))}")
    _write_recording(record_path, seed, state, records, llm_mode=_llm_mode(args))
    return 0


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


def _run_character_creation_flow(state: GameState) -> None:
    print("Create your islander.")
    rerolled = False
    while True:
        archetype_ids = list(PLAYER_ARCHETYPES)
        for index, archetype_id in enumerate(archetype_ids, start=1):
            archetype = PLAYER_ARCHETYPES[archetype_id]
            stats = DEFAULT_ARCHETYPE_STATS[archetype_id]
            print(
                f"{index}. {archetype.display_name} "
                f"(+{archetype.stat_bonus_value} {archetype.stat_bonus_name}; "
                f"{_stats_text(stats)})"
            )
        raw = input("archetype> ").strip()
        try:
            selected = archetype_ids[int(raw) - 1]
        except (ValueError, IndexError):
            print("choose an archetype number")
            continue
        stats = DEFAULT_ARCHETYPE_STATS[selected]
        print("Press Enter to accept these stats, type five numbers, or type reroll.")
        print(_stats_text(stats))
        stat_raw = input("stats> ").strip()
        if stat_raw.lower() == "reroll":
            if rerolled:
                print("reroll already used")
            else:
                rerolled = True
                print("Reroll used. Pick again.")
            continue
        if stat_raw:
            try:
                stats = _parse_stats(stat_raw)
            except ValueError as exc:
                print(exc)
                continue
        create_character(state, archetype_id=selected, stats=stats, rerolled=rerolled)
        _print_character_card(state)
        return


def _parse_stats(raw: str) -> PlayerStats:
    pieces = [int(piece) for piece in raw.replace(",", " ").split()]
    if len(pieces) != 5:
        raise ValueError("enter five stats: charm banter eq graft loyalty")
    return PlayerStats(charm=pieces[0], banter=pieces[1], eq=pieces[2], graft=pieces[3], loyalty=pieces[4])


def _stats_text(stats: PlayerStats) -> str:
    return (
        f"Charm {stats.charm}, Banter {stats.banter}, EQ {stats.eq}, "
        f"Graft {stats.graft}, Loyalty {stats.loyalty}"
    )


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
    raw_creation = package.get("character_creation")
    if isinstance(raw_creation, dict):
        creation = CharacterCreation.model_validate(raw_creation)
        create_character(
            state,
            archetype_id=creation.archetype_id,
            stats=creation.stats,
            rerolled=creation.rerolled,
        )
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
        "villa_snapshot": _villa_snapshot(state),
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


def _villa_snapshot(state: GameState) -> dict[str, list[str]]:
    snapshot: dict[str, list[str]] = {}
    for location in Location:
        occupants = ["you"] if location is state.location_id else []
        occupants.extend(
            islander.name
            for islander in state.islanders
            if islander.location_id is location and not islander.eliminated
        )
        snapshot[location.value] = occupants
    return snapshot


def _write_recording(
    path: Path | None,
    seed: int,
    state: GameState,
    records: list[dict[str, Any]],
    *,
    llm_mode: str,
) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    package = {
        "seed": seed,
        "llm_mode": llm_mode,
        "character_creation": (
            None if state.character_creation is None else state.character_creation.model_dump(mode="json")
        ),
        "final_hash": state_hash(state_hash_payload(state)),
        "records": records,
        "final_state": state.model_dump(mode="json"),
    }
    path.write_text(json.dumps(package, indent=2), encoding="utf-8")


def _llm_mode(args: argparse.Namespace) -> str:
    return "mock" if args.mock_llm else "real"


__all__ = ["_print_state", "_print_villa_update", "add_parser", "run"]
