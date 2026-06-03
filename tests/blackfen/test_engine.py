from pathlib import Path

from src.blackfen.engine import run_turn
from src.blackfen.hash import state_hash
from src.blackfen.models import RunStatus
from src.blackfen.new_game import new_game
from src.blackfen.rng import SeededRng
from src.blackfen.scenario import load_action_script, run_action_script


def test_victory_fixture_reaches_victory_hash() -> None:
    script = load_action_script(Path("tests/blackfen/fixtures/victory-path.yaml"))
    result = run_action_script(script)
    assert result.state.status is RunStatus.VICTORY
    assert result.final_hash == "fe36c434c6295477"


def test_same_seed_and_actions_are_deterministic() -> None:
    script = load_action_script(Path("tests/blackfen/fixtures/victory-path.yaml"))
    first = run_action_script(script)
    second = run_action_script(script)
    assert first.final_hash == second.final_hash


def test_death_ends_the_run() -> None:
    state = new_game(7, player_name="Ash", class_id="mage")
    rng = SeededRng(7)
    state.current_location_id = "barrow_crypt"
    state.known_locations.append("barrow_crypt")
    state.quest_flags.extend(["has_shrine_bell", "barrow_opened"])
    state.player.hp = 1
    state.player.armor_class = 1
    for _ in range(3):
        if state.status is not RunStatus.ACTIVE:
            break
        run_turn(state, "attack", rng)
    assert state.status is RunStatus.DEAD
    ended_hash = state_hash(state)
    try:
        run_turn(state, "attack", rng)
    except ValueError as exc:
        assert "ended" in str(exc)
    else:
        raise AssertionError("dead runs must reject further turns")
    assert state_hash(state) == ended_hash

