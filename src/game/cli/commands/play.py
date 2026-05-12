"""Interactive play command."""

from __future__ import annotations

import argparse
import sys

from src.game.agents.event_narrator import OpenAIEventNarrator
from src.game.agents.islander_voice import OpenAIIslanderVoice
from src.game.engine.actions import ActionKind, ActionSpec, PlayerAction, available_actions
from src.game.engine.intents import IntentCategory, available_intents_for
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
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    if args.snapshot:
        print("play --snapshot is not implemented yet", file=sys.stderr)
        return 2

    seed = 1 if args.seed is None else args.seed
    state = new_game(seed)
    rng = SeededRng(seed)
    islander_voice = None if args.mock_llm else OpenAIIslanderVoice().generate
    event_narrator = None if args.mock_llm else OpenAIEventNarrator().narrate
    print("Game CLI. Type a number, /state, /hash, /help, or /quit.")

    while not state.is_terminal:
        _print_state(state)
        actions = available_actions(state)
        _print_actions(actions)
        raw = input("> ").strip()
        if raw in {"/quit", "quit", "q"}:
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

        turn = run_turn(
            state,
            action,
            rng,
            islander_voice=islander_voice,
            event_narrator=event_narrator,
        )
        state = turn.state
        _print_turn(turn)

    print("Day complete.")
    print(f"final hash: {state_hash(state_hash_payload(state))}")
    return 0


def _print_state(state: GameState, *, debug: bool = False) -> None:
    print(f"\nDay {state.day} | {state.phase.value} | turn {state.turn_index}")
    print(f"Location: {state.location_id}")
    for islander in state.islanders:
        detail = f" affection={islander.relationship.affection}" if debug else ""
        print(f"- {islander.name} ({islander.archetype}){detail}")


def _print_actions(actions: list[ActionSpec]) -> None:
    for index, spec in enumerate(actions, start=1):
        print(f"{index}. {spec.label}")


def _print_turn(turn: TurnResult) -> None:
    result = turn.mechanical_result
    if turn.exchange is not None:
        print(f'You: "{turn.exchange.player_dialogue}"')
        print(f'{_target_name(turn)}: {turn.exchange.npc_dialogue}')
    if turn.event_narration is not None:
        print(turn.event_narration.prose)
    if result.roll is not None and result.success_chance is not None:
        outcome = "success" if result.success else "miss"
        print(f"{outcome}: rolled {result.roll} vs {result.success_chance}")
    print(f"hash: {turn.state_hash}")


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
