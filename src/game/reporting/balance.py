"""Balance simulation for report packets."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from src.game.engine.scenario import ActionScript, load_action_script, run_action_script


def run_balance(seeds: int, script_path: Path) -> tuple[Counter[str], Counter[str]]:
    """Run mock-narrated deterministic simulations and count outcomes/actions."""
    outcomes: Counter[str] = Counter()
    actions: Counter[str] = Counter()
    base = load_action_script(script_path)
    for seed in range(1, seeds + 1):
        script = ActionScript(
            name=f"{base.name}-{seed}",
            seed=seed,
            player_stats=base.player_stats,
            actions=base.actions,
        )
        result = run_action_script(script)
        outcomes[result.state.phase.value] += 1
        for action in script.actions:
            actions[action.kind.value] += 1
    return outcomes, actions
