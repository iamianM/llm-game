# QA Strategy

The goal is for the CLI, browser, and tests to exercise the same engine with the same actions, snapshots, hashes, and traces.

## Principles

1. One engine, one truth.
2. Deterministic by default.
3. Engine correctness and narrator quality are separate test currencies.
4. Snapshots are first-class debugging infrastructure.
5. `make qa` is the completion gate for implementation work, and it must only include checks that verify real behavior.

## Test Layers

| Layer | Where | What it proves | Default? | LLM? |
|---|---|---|---|---|
| L1 Static | ruff, mypy, content lint | Code parses, types align, content refs resolve | yes | no |
| L2 Unit | `tests/engine/` | Pure functions match design contracts | yes | no |
| L3 Property | `tests/engine/*_props.py` | Invariants hold over generated cases | yes | no |
| L4 Scenario | `tests/scenarios/fixtures/` | Seed + snapshot + actions yields expected hash | yes | no |
| L5 E2E | `tests/scenarios/e2e/` | Full no-LLM day, save/load, API parity | yes | no |
| L6 Narrator | `tests/agents/` | Narration quality and contract compliance | opt-in | yes |

L1-L5 are the current non-LLM gate. L6 is marked `llm`, opt-in, and cost-capped.

## Required Gates

`make qa` runs the honest non-LLM gate:

1. `make lint`
2. `make type-check`
3. `make content-lint`
4. `make test`
5. `make smoke`
6. `make determinism`

`make smoke` replays `scripts/fixtures/day1-happy-path.yaml`. `make determinism` verifies checked-in scenario fixtures and expected hashes.

If a change touches Pydantic state models, also verify checked-in snapshots still load or regenerate them intentionally.

If a change touches prompts or agents, run mock narration tests. Run `make test-llm` only when real narrator behavior changed and budget allows.

## Snapshot Contract

A snapshot contains:

- schema version
- `GameState`
- RNG state
- turn index
- active day and phase
- state hash

The same snapshot can be loaded by CLI, FastAPI/browser, or pytest.

## Trace Contract

Every turn trace records:

- input state hash
- action
- RNG rolls
- mechanical result
- narration or mock narration
- LLM metadata when present
- output state hash

Trace artifacts are the common debugging currency for users and AI assistants.

## Browser / CLI / Test Parity

- `ActionKind` is the single source of action vocabulary.
- Pydantic state models are the source for generated browser types.
- `engine.run_turn(state, action)` is the only state mutation path.
- CLI, FastAPI routes, and tests all call the same engine.
- State hash must match across all surfaces for the same snapshot and action script.
