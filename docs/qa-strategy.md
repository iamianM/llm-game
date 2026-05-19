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
| L7 Docs Health | `scripts/docs-health.py` | Contract-sensitive files changed with their owning docs | local hook / targeted | no |

L1-L5 are the current non-LLM gate. L6 is marked `llm` and opt-in.

## Required Gates

`make qa` runs the honest non-LLM gate:

1. `make lint`
2. `make type-check`
3. `make content-lint`
4. `make test` (parallel non-LLM pytest via `pytest-xdist`)
5. `make smoke`
6. `make determinism`

`make docs-health` is a fast structural guard for contract-sensitive changes. It is intentionally outside the default gate until the map is tuned enough to stay low-friction.

`make smoke` verifies `tests/scenarios/fixtures/day1-happy-path.yaml`. `make determinism` verifies checked-in scenario fixtures and expected hashes.

If a change touches Pydantic state models, also verify checked-in snapshots still load or regenerate them intentionally.

If a change touches prompts or agents, run mock agent tests. Run `make test-llm` when real agent behavior changed.

Recorded playthroughs also run structural pacing checks: average actions per phase, day progression, time-expired advances, NPC-initiated exits, and NPC arrival rolls. These stay deterministic and do not use an LLM judge.

## Docs Health

Documentation health checks should be structural, not semantic prose checks.

- Use `docs/contract-map.yaml` to map contract-sensitive source paths to owning docs.
- The staged-file check fails only when a mapped source path changes without at least one mapped doc changing in the same staged set.
- Do not add checks that scan prose for forbidden words, brand vocabulary, or prompt quality. Fix those at the source through typed display identifiers, prompt ownership, authored content, or tests around structured fields.
- Keep hooks fast enough to run before every commit. Full `make qa`, web builds, Playwright, and LLM tests belong outside the hook.

Install the local hook with:

```bash
git config core.hooksPath .githooks
```

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
