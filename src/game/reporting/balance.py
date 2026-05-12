"""Balance simulation for report packets."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from src.game.agents.contextual_options import mock_follow_up_menu
from src.game.agents.islander_voice import Exchange
from src.game.engine.actions import ActionKind, ActionSpec, PlayerAction, available_actions
from src.game.engine.intents import available_intents_for
from src.game.engine.rules import MechanicalResult
from src.game.engine.turn import run_turn
from src.game.state.models import FollowUpMenu, GameState, PlayerStats, new_game
from src.game.state.rng import SeededRng

MAX_BALANCE_TURNS = 120
FOLLOW_UP_INTENTS = [
    "joke_back",
    "go_deeper",
    "honest_vulnerable",
    "escalate_flirt",
    "apologize",
    "deflect_with_humor",
]


def run_balance(seeds: int, _script_path: Path) -> tuple[Counter[str], Counter[str]]:
    """Run varied mock-narrated simulations and count outcomes/actions.

    The script path is accepted for CLI compatibility, but balance runs choose
    from the live valid-action surface so the report measures engine behavior
    across seeds instead of replaying one fixed path.
    """
    outcomes: Counter[str] = Counter()
    actions: Counter[str] = Counter()
    for seed in range(1, seeds + 1):
        state = new_game(seed, player_stats=_stats_for_seed(seed))
        rng = SeededRng(seed)
        chooser = rng.fork("balance-policy")
        contextual = _balance_contextual_options(seed)
        for turn_index in range(MAX_BALANCE_TURNS):
            specs = available_actions(state)
            if not specs:
                break
            action = _choose_action(state, specs, chooser.fork(f"turn-{turn_index}"))
            turn = run_turn(state, action, rng, contextual_options=contextual)
            state = turn.state
            actions[_action_key(turn.mechanical_result.action)] += 1
            if state.is_terminal:
                break
        outcomes[_outcome_key(state)] += 1
    return outcomes, actions


def _stats_for_seed(seed: int) -> PlayerStats:
    profiles = [
        PlayerStats(charm=8, banter=7, eq=6, graft=6, loyalty=3),
        PlayerStats(charm=6, banter=8, eq=5, graft=8, loyalty=3),
        PlayerStats(charm=6, banter=6, eq=8, graft=4, loyalty=6),
        PlayerStats(charm=7, banter=5, eq=7, graft=5, loyalty=6),
    ]
    return profiles[(seed - 1) % len(profiles)]


def _choose_action(state: GameState, specs: list[ActionSpec], rng: SeededRng) -> PlayerAction:
    if state.active_conversation is not None:
        respond = [spec for spec in specs if spec.action.kind is ActionKind.RESPOND_WITH]
        end = [spec for spec in specs if spec.action.kind is ActionKind.END_CONVERSATION]
        if respond and rng.randint(1, 100) <= 72:
            return rng.choice(respond).action
        if end:
            return end[0].action

    starts = [spec for spec in specs if spec.action.kind is ActionKind.START_CONVERSATION]
    moves = [spec for spec in specs if spec.action.kind is ActionKind.MOVE]
    advance = [spec for spec in specs if spec.action.kind is ActionKind.ADVANCE_PHASE]

    roll = rng.randint(1, 100)
    if advance and state.day >= 4 and roll <= 70:
        return advance[0].action
    if starts and roll <= 58:
        spec = rng.choice(starts)
        target_id = spec.action.target_id
        if target_id is None:
            raise ValueError("START_CONVERSATION spec missing target_id")
        intents = available_intents_for(state, target_id)
        intent = rng.choice(intents)
        return PlayerAction(
            kind=ActionKind.START_CONVERSATION,
            target_id=target_id,
            intent_id=intent.id,
        )
    if moves and roll <= 80:
        return rng.choice(moves).action
    if advance:
        return advance[0].action
    return rng.choice(specs).action


def _balance_contextual_options(seed: int):
    counter = 0

    def contextual_options(
        _state: GameState,
        _result: MechanicalResult,
        _exchange: Exchange,
        probability: int,
    ) -> FollowUpMenu:
        nonlocal counter
        intent_kind = FOLLOW_UP_INTENTS[(seed + counter) % len(FOLLOW_UP_INTENTS)]
        counter += 1
        return mock_follow_up_menu(
            intent_kind=intent_kind,
            npc_will_leave=probability >= 75,
        )

    return contextual_options


def _action_key(action: PlayerAction) -> str:
    if action.kind in {ActionKind.START_CONVERSATION, ActionKind.RESPOND_WITH}:
        return f"{action.kind.value}:{action.intent_id or 'unknown'}"
    if action.kind is ActionKind.MOVE:
        return f"move:{action.target_id}"
    return action.kind.value


def _outcome_key(state: GameState) -> str:
    if state.player.eliminated:
        return f"eliminated_day_{state.day}"
    if state.is_terminal:
        coupled = any(
            couple.partner_a_id == "player" or couple.partner_b_id == "player"
            for couple in state.couples
        )
        return "complete_coupled" if coupled else "complete_single"
    return f"unfinished_day_{state.day}_{state.phase.value}"
