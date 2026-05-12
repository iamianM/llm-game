# Build Log

Append-only implementation log for `docs/build-plan-A2-E.md`.

## Phase A1 closeout

- Files added: `tests/engine/test_models.py`
- Files changed: `src/game/agents/narrator.py`, `src/game/engine/turn.py`, `tests/engine/test_turn.py`, `Makefile`, `AGENTS.md`, `docs/qa-strategy.md`
- Tests added: model extra-field rejection, relationship clamp bounds, snapshot hash roundtrip, turn-index mutation boundary
- QA result: `make qa` green, 17 tests passed
- Scenario fixture: `tests/scenarios/fixtures/day1-happy-path.yaml`

## Phase A2

- Files added: `tests/scenarios/fixtures/day1-flirt-mixed.yaml`
- Files changed: `src/game/state/models.py`, `src/game/engine/actions.py`, `src/game/engine/rules.py`, `src/game/agents/narrator.py`, `tests/engine/test_actions.py`, `tests/engine/test_rules.py`
- Tests added: flirt success and miss deltas, typed relationship-delta validation, FLIRT action availability
- QA result: `make qa` green, 21 tests passed
- Scenario fixture: `tests/scenarios/fixtures/day1-flirt-mixed.yaml`

## Phase A3

- Files added: `tests/scenarios/fixtures/day1-full-stats.yaml`, `tests/scenarios/fixtures/day1-low-stats.yaml`
- Files changed: `src/game/state/models.py`, `src/game/engine/actions.py`, `src/game/engine/rules.py`, `src/game/engine/scenario.py`, `tests/engine/test_actions.py`, `tests/engine/test_models.py`, `tests/engine/test_rules.py`
- Tests added: stat-budget validation, bold-flirt gate, LISTEN deltas, BOLD_FLIRT deltas
- QA result: `make qa` green, 28 tests passed
- Scenario fixture: `tests/scenarios/fixtures/day1-full-stats.yaml`

## Phase B

- Files added: `src/game/engine/simulation.py`, `tests/engine/test_simulation.py`, `tests/scenarios/fixtures/day6-full-run.yaml`
- Files changed: `src/game/state/models.py`, `src/game/engine/actions.py`, `src/game/engine/phases.py`, `src/game/engine/rules.py`, `src/game/engine/turn.py`, scenario fixtures
- Tests added: location filtering, move validation, multi-day phase rollover, deterministic off-screen simulation
- QA result: `make qa` green, 32 tests passed
- Scenario fixture: `tests/scenarios/fixtures/day6-full-run.yaml`

## Phase C

- Files added: `src/game/engine/ceremonies.py`, `tests/engine/test_ceremonies.py`, `tests/scenarios/fixtures/recoupling-day3.yaml`, `tests/scenarios/fixtures/bombshell-day4.yaml`, `tests/scenarios/fixtures/elimination-day5.yaml`
- Files changed: `src/game/state/models.py`, `src/game/engine/rules.py`, `src/game/engine/turn.py`, scenario fixture hashes
- Tests added: recoupling partner choice, leftover elimination, bombshell idempotency, public-perception bounds
- QA result: `make qa` green, 39 tests passed
- Scenario fixture: `tests/scenarios/fixtures/recoupling-day3.yaml`

## Phase D

- Files added: runtime archetype/location content, `tests/agents/test_narrator_quality.py`, `fixtures/snapshots/phaseD-narrated-session.json`, `fixtures/traces/phaseD-narrated-session.json`
- Files changed: `src/game/agents/narrator.py`, `src/game/content/*`, `src/game/engine/turn.py`, `src/game/cli/commands/play.py`
- Tests added: opt-in real Narrator contract tests for bounded prose and visible-context safety
- QA result: `make qa` green, 39 tests passed; `uv run pytest -m llm` green, 5 tests passed
- Scenario fixture: `tests/scenarios/fixtures/day6-full-run.yaml`; model used: `gpt-4o-mini` via verified `OPENAI_API_KEY`

## Phase E

- Files added: `src/game/reporting/*`, `src/game/cli/commands/report.py`, policy scripts, `review-packet/`
- Files changed: `src/game/cli/__main__.py`
- Tests added: command-level packet generation and link validation via local run; no new pytest module
- QA result: `make qa` green, 39 tests passed; packet generated with real narration and opened locally at `http://127.0.0.1:8766/index.html`
- Scenario fixture: `scripts/fixtures/policy-loyal.yaml`, `scripts/fixtures/policy-chaotic.yaml`, `scripts/fixtures/policy-strategic.yaml`

## Phase E.1

- Files added: none
- Files changed: `src/game/engine/turn.py`, `src/game/engine/simulation.py`, `src/game/engine/ceremonies.py`, `src/game/agents/narrator.py`, `pyproject.toml`, scenario fixtures
- Tests added: off-screen NPC chat does not mutate player relationships; turn results surface bombshell events
- QA result: `make qa` green, 41 tests passed
- Scenario fixture: existing fixtures regenerated after cosmetic-only NPC simulation and visible ceremony events

## Phase F1

- Files added: `content/intents.yaml`, `src/game/engine/intents.py`, `tests/engine/test_intents.py`
- Files changed: `src/game/state/models.py`, `src/game/engine/actions.py`, `src/game/engine/rules.py`, `src/game/cli/commands/play.py`, scenario fixtures
- Tests added: intent catalog coverage, intent unlock thresholds, START_CONVERSATION validation, typed intent deltas
- QA result: `make qa` green, 39 tests passed
- Scenario fixture: existing fixtures regenerated for the schema v4 tiered intent vocabulary

## Phase F2

- Files added: `src/game/agents/event_narrator.py`, `src/game/agents/prompts/event_narrator.md`, `tests/agents/test_event_narrator.py`, `review-packet-preview/session-phaseF2.html`
- Files changed: `src/game/agents/islander_voice.py`, `src/game/agents/prompts/islander_voice.md`, `src/game/engine/turn.py`, `src/game/cli/commands/play.py`, `src/game/cli/commands/report.py`, `src/game/reporting/html.py`
- Tests added: real Islander Voice contract coverage across all 12 intents; real Event Narrator coverage for bombshell, recoupling, and elimination; state hash excludes dialogue text
- QA result: `make qa` green, 40 tests passed; `make test-llm` green, 15 tests passed
- Scenario fixture: existing deterministic fixtures unchanged; F2 preview generated at `review-packet-preview/session-phaseF2.html`
