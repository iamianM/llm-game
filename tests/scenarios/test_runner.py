"""YAML scenario runner.

Design sources:
- docs/systems/qa.md: L4 Scenario
- docs/decisions/0008-snapshot-and-trace-architecture.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.game.engine.scenario import assert_expected_hash, load_action_script, run_action_script


@pytest.mark.parametrize("fixture", sorted(Path("tests/scenarios/fixtures").glob("*.yaml")))
def test_scenario_fixture_hash(fixture: Path) -> None:
    """Replay each checked-in scenario and assert its final hash."""
    result = run_action_script(load_action_script(fixture))
    assert_expected_hash(result)
