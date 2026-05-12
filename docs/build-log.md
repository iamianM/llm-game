# Build Log

Append-only implementation log for `docs/build-plan-A2-E.md`.

## Phase A1 closeout

- Files added: `tests/engine/test_models.py`
- Files changed: `src/game/agents/narrator.py`, `src/game/engine/turn.py`, `tests/engine/test_turn.py`, `Makefile`, `AGENTS.md`, `docs/qa-strategy.md`
- Tests added: model extra-field rejection, relationship clamp bounds, snapshot hash roundtrip, turn-index mutation boundary
- QA result: `make qa` green, 17 tests passed
- Scenario fixture: `tests/scenarios/fixtures/day1-happy-path.yaml`
