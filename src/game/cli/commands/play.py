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
from src.game.agents.heartbreaker_voice import OpenAIHeartbreakerVoice
from src.game.agents.resort_orchestrator import OpenAIResortOrchestrator
from src.game.cli.commands.play_recording import (
    llm_mode as _llm_mode,
)
from src.game.cli.commands.play_recording import (
    record_from_turn as _record_from_turn,
)
from src.game.cli.commands.play_recording import (
    trace_mode as _trace_mode,
)
from src.game.cli.commands.play_recording import (
    write_recording as _write_recording,
)
from src.game.cli.commands.play_render import (
    print_actions as _print_actions,
)
from src.game.cli.commands.play_render import (
    print_background_history as _print_background_history,
)
from src.game.cli.commands.play_render import (
    print_character_card as _print_character_card,
)
from src.game.cli.commands.play_render import (
    print_resort_update as _print_resort_update,
)
from src.game.cli.commands.play_render import (
    print_state as _print_state,
)
from src.game.cli.commands.play_render import (
    print_turn as _print_turn,
)
from src.game.engine.actions import ActionKind, PlayerAction, available_actions
from src.game.engine.character_creation import (
    DEFAULT_ARCHETYPE_STATS,
    PLAYER_ARCHETYPES,
    create_character,
)
from src.game.engine.intents import IntentCategory, available_intents_for
from src.game.engine.recorded_agents import RecordedAgents
from src.game.engine.turn import run_turn
from src.game.state.models import CharacterCreation, GameState, Gender, PlayerStats, new_game
from src.game.state.rng import SeededRng
from src.game.state.snapshot import (
    load_checkpoint,
    save_auto_checkpoint,
    save_named_checkpoint,
    state_hash,
    state_hash_payload,
)


def add_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the play command."""
    parser = subparsers.add_parser("play", help="start an interactive CLI game")
    parser.add_argument("--seed", type=int, help="seed for a new run")
    parser.add_argument("--mock-llm", action="store_true", help="use deterministic mock narration")
    parser.add_argument("--trace", action="store_true", help="write turn traces")
    parser.add_argument("--record", help="record this live session to a trace package")
    parser.add_argument("--replay", help="replay a recorded trace package without LLM calls")
    parser.add_argument("--from-checkpoint", help="resume from a named checkpoint or checkpoint path")
    parser.add_argument("--branch-name", help="branch name for checkpoint resume trace output")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    from_checkpoint = getattr(args, "from_checkpoint", None)
    if args.record and args.replay:
        print("choose either --record or --replay, not both")
        return 2
    if args.replay:
        return _replay_recording(Path(args.replay))

    records: list[dict[str, Any]]
    rng_state: list[object] | None = None
    if from_checkpoint:
        state, loaded_records, checkpoint_seed, checkpoint_rng_state = load_checkpoint(from_checkpoint)
        records = loaded_records
        seed = checkpoint_seed if args.seed is None else args.seed
        if args.seed is None:
            rng_state = checkpoint_rng_state
    else:
        seed = 1 if args.seed is None else args.seed
        state = new_game(seed)
        records = []
    rng = SeededRng.from_snapshot(seed, rng_state) if rng_state is not None else SeededRng(seed)
    heartbreaker_voice = None if args.mock_llm else OpenAIHeartbreakerVoice().generate
    contextual_options = None if args.mock_llm else ContextualOptionsAgent().generate
    event_narrator = None if args.mock_llm else OpenAIEventNarrator().narrate
    conversation_curator = None if args.mock_llm else OpenAIConversationCurator().curate
    resort_orchestrator = None if args.mock_llm else OpenAIResortOrchestrator().decide
    background_dialogue = None if args.mock_llm else OpenAIBackgroundDialogue().generate
    record_path = _record_path_from_args(args)
    if not from_checkpoint:
        _run_character_creation_flow(state)
    print("Game CLI. Type a number, /state, /background, /hash, /help, or /quit.")

    while not state.is_terminal:
        _print_state(state)
        actions = available_actions(state)
        _print_actions(actions)
        raw = input("> ").strip()
        if raw in {"/quit", "quit", "q"}:
            _write_recording(record_path, seed, state, records, llm_mode=_llm_mode(args), mode=_trace_mode(args), persona="")
            return 0
        if raw == "/help":
            print(
                "Commands: /state, /background, /hash, /help, /quit. Choose actions by number. "
                "Wheel exit options close gracefully; Walk away is curt."
            )
            continue
        if raw == "/state":
            _print_state(state, debug=True)
            continue
        if raw == "/background":
            _print_background_history(records)
            continue
        if raw.startswith("/checkpoint"):
            name = raw.removeprefix("/checkpoint").strip() or f"turn-{state.turn_index}"
            path = save_named_checkpoint(state, name, records, seed=seed, rng_state=rng.snapshot())
            print(f"checkpoint saved: {path}")
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
            heartbreaker_voice=heartbreaker_voice,
            contextual_options=contextual_options,
            event_narrator=event_narrator,
            conversation_curator=conversation_curator,
            resort_orchestrator=resort_orchestrator,
            background_dialogue=background_dialogue,
        )
        state = turn.state
        records.append(_record_from_turn(input_hash, action, turn))
        if _should_auto_checkpoint(turn):
            save_auto_checkpoint(state, seed, records, rng_state=rng.snapshot())
        _write_recording(record_path, seed, state, records, llm_mode=_llm_mode(args), mode=_trace_mode(args), persona="")
        _print_turn(turn)

    print("Day complete.")
    print(f"final hash: {state_hash(state_hash_payload(state))}")
    _write_recording(record_path, seed, state, records, llm_mode=_llm_mode(args), mode=_trace_mode(args), persona="")
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
    print("Create your heartbreaker.")
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
        gender = _choose_gender()
        create_character(state, archetype_id=selected, gender=gender, stats=stats, rerolled=rerolled)
        _print_character_card(state)
        return


def _choose_gender() -> Gender:
    while True:
        print("Gender:")
        print("  1. Man")
        print("  2. Woman")
        raw = input("gender> ").strip()
        if raw == "1" or raw.lower() == "man":
            return Gender.MAN
        if raw == "2" or raw.lower() == "woman":
            return Gender.WOMAN
        print("choose 1 for man or 2 for woman")


def _parse_stats(raw: str) -> PlayerStats:
    pieces = [int(piece) for piece in raw.replace(",", " ").split()]
    if len(pieces) != 5:
        raise ValueError("enter five stats: charm banter eq spark loyalty")
    return PlayerStats(charm=pieces[0], banter=pieces[1], eq=pieces[2], spark=pieces[3], loyalty=pieces[4])


def _stats_text(stats: PlayerStats) -> str:
    return (
        f"Charm {stats.charm}, Banter {stats.banter}, EQ {stats.eq}, "
        f"Spark {stats.spark}, Loyalty {stats.loyalty}"
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
            gender=creation.gender,
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
            heartbreaker_voice=agents.heartbreaker_voice if raw_record.get("exchange") is not None else None,
            contextual_options=(
                agents.contextual_options if raw_record.get("follow_up_menu") is not None else None
            ),
            event_narrator=(
                agents.event_narrator if raw_record.get("event_narration") is not None else None
            ),
            conversation_curator=agents.conversation_curator,
            resort_orchestrator=agents.resort_orchestrator,
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


__all__ = ["_print_state", "_print_resort_update", "add_parser", "run"]


def _record_path_from_args(args: argparse.Namespace) -> Path | None:
    if args.record is not None:
        return Path(args.record)
    from_checkpoint = getattr(args, "from_checkpoint", None)
    branch_name = getattr(args, "branch_name", None)
    if from_checkpoint and branch_name:
        checkpoint_stem = Path(str(from_checkpoint)).stem
        return Path(".game_traces") / f"{checkpoint_stem}_{branch_name}.json"
    return None


def _should_auto_checkpoint(turn: object) -> bool:
    from src.game.engine.turn import TurnResult

    if not isinstance(turn, TurnResult):
        return False
    action_kind = turn.mechanical_result.action.kind.value
    return bool(
        turn.auto_advance
        or turn.ceremony_events
        or action_kind in {"private_suite", "flush_decision", "join_gather"}
    )


