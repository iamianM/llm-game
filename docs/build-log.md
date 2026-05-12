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

## Phase F2.1

- Files added: `src/game/agents/prompts/contextual_options.md` for the Phase F3 follow-up menu agent
- Files changed: `src/game/agents/prompts/islander_voice.md`, `src/game/agents/prompts/event_narrator.md`, `src/game/agents/islander_voice.py`, `src/game/agents/event_narrator.py`, `src/game/cli/commands/report.py`, `src/game/reporting/html.py`, `ENGINEERING.md`, `docs/build-plan-F.md`, `docs/build-plan-A2-E.md`
- Tests added: none; existing agent and engine contracts still cover the behavior
- QA result: `make qa` green, 40 tests passed; `make test-llm` green, 15 tests passed
- Mid-phase gate: F2 preview regenerated at `review-packet-preview/session-phaseF2.html`

## Phase F3

- Files added: `src/game/agents/contextual_options.py`, `src/game/engine/conversation.py`, `tests/agents/test_contextual_options.py`, `tests/engine/test_conversation.py`, `tests/scenarios/fixtures/conversation-multi-exchange.yaml`
- Files changed: `src/game/state/models.py`, `src/game/state/snapshot.py`, `src/game/engine/actions.py`, `src/game/engine/intents.py`, `src/game/engine/rules.py`, `src/game/engine/scenario.py`, `src/game/engine/turn.py`, `src/game/cli/commands/play.py`, `src/game/cli/commands/report.py`, `src/game/reporting/balance.py`, `src/game/reporting/html.py`, policy scripts, scenario fixtures, `review-packet/`
- Tests added: conversation lifecycle, departure probability, hash exclusion for dialogue text, active-conversation action validation, real Contextual Options contract tests, multi-exchange scenario replay
- QA result: Make is not installed in this PowerShell session, so the Makefile targets were run directly: `ruff`, `mypy`, `content lint`, non-LLM pytest, smoke replay, fixture determinism all green; `make test-llm` equivalent green, 25 LLM tests passed
- Scenario fixture: `tests/scenarios/fixtures/conversation-multi-exchange.yaml`
- Packet: regenerated with real LLM calls at `review-packet/index.html` and inspected locally at `http://127.0.0.1:8771/index.html`

## Phase G1

- Files added: `docs/build-plan-G.md`
- Files changed: `src/game/state/models.py`, `src/game/agents/contextual_options.py`, `src/game/agents/prompts/contextual_options.md`, `src/game/engine/actions.py`, `src/game/cli/commands/play.py`, `src/game/reporting/html.py`, scenario fixtures
- Tests added: existing Contextual Options LLM tests now validate short labels, categories, exit options, and threshold-safe parsed output
- QA result: Make is not installed in this PowerShell session, so the Makefile targets were run directly: `ruff`, `mypy`, `content lint`, non-LLM pytest, smoke replay, fixture determinism all green; Contextual Options LLM subset green, 10 tests passed
- Scenario fixture: existing fixtures regenerated for schema v6 short-label follow-up menu shape

## Phase G2

- Files added: none
- Files changed: `src/game/engine/rules.py`, `tests/engine/test_rules.py`, `tests/scenarios/fixtures/conversation-multi-exchange.yaml`
- Tests added: vulnerable follow-up trust gain, missed flirt chemistry loss, unknown follow-up intent failure, high-risk delta scaling
- QA result: Make is not installed in this PowerShell session, so the Makefile targets were run directly: `ruff`, `mypy`, `content lint`, non-LLM pytest, smoke replay, fixture determinism all green; 51 non-LLM tests passed
- Scenario fixture: `tests/scenarios/fixtures/conversation-multi-exchange.yaml` regenerated after follow-up deltas became mechanical

## Phase G3

- Files added: `src/game/engine/memory.py`, `tests/engine/test_memory.py`
- Files changed: `src/game/state/models.py`, `src/game/state/snapshot.py`, `src/game/engine/turn.py`, `tests/engine/test_models.py`, scenario fixtures
- Tests added: conversation close creates player/NPC memories, deterministic memory ids, ceremony memories, memory content excluded from state hash
- QA result: Make is not installed in this PowerShell session, so the Makefile targets were run directly: `ruff`, `mypy`, `content lint`, non-LLM pytest, smoke replay, fixture determinism all green; 55 non-LLM tests passed
- Scenario fixture: existing fixtures regenerated for schema v7 memory metadata

## Phase G4

- Files added: none
- Files changed: `src/game/engine/simulation.py`, `tests/engine/test_simulation.py`, scenario fixtures
- Tests added: off-screen chat creates memories for both NPCs, drama memories are high-weight, chemistry can pull NPCs toward the player location
- QA result: Make is not installed in this PowerShell session, so the Makefile targets were run directly: `ruff`, `mypy`, `content lint`, non-LLM pytest, smoke replay, fixture determinism all green; 58 non-LLM tests passed
- Scenario fixture: `tests/scenarios/fixtures/day6-full-run.yaml` now accumulates NPC memories through day six

## Phase G5

- Files added: `tests/engine/test_gossip.py`
- Files changed: `src/game/state/models.py`, `src/game/state/snapshot.py`, `src/game/engine/conversation.py`, `src/game/engine/rules.py`, `src/game/engine/turn.py`, `src/game/agents/contextual_options.py`, `src/game/agents/islander_voice.py`, `tests/scenarios/fixtures/conversation-multi-exchange.yaml`
- Tests added: gossip appears from eligible NPC memories, gossip transfers memories to the player, affection threshold locks gossip, gossip offer content is hash-excluded
- QA result: Make is not installed in this PowerShell session, so the Makefile targets were run directly: `ruff`, `mypy`, `content lint`, non-LLM pytest, smoke replay, fixture determinism all green; 62 non-LLM tests passed
- Scenario fixture: `tests/scenarios/fixtures/conversation-multi-exchange.yaml` regenerated after the mock follow-up exit menu became single-exit only

## Phase G3 corrective

- Files added: `src/game/agents/conversation_curator.py`, `tests/agents/test_conversation_curator.py`
- Files changed: `src/game/state/models.py`, `src/game/engine/memory.py`, `src/game/engine/turn.py`, scenario fixtures
- Tests added: mock curator emits participant memories, real Conversation Curator output validates as a typed `MemoryBatch`
- QA result: Make is not installed in this PowerShell session, so the Makefile targets were run directly: `ruff`, `mypy`, `content lint`, non-LLM pytest, smoke replay, fixture determinism all green; 63 non-LLM tests passed; curator LLM subset green, 1 LLM test passed
- Scenario fixture: existing fixtures regenerated for schema v8 and typed curator memory commits

## Phase G4 corrective

- Files added: `src/game/agents/villa_orchestrator.py`, `src/game/agents/background_dialogue.py`, `src/game/engine/villa.py`, `tests/agents/test_villa_orchestrator.py`, `tests/agents/test_background_dialogue.py`, `tests/engine/test_villa.py`
- Files changed: `src/game/state/models.py`, `src/game/state/snapshot.py`, `src/game/agents/conversation_curator.py`, `src/game/engine/turn.py`, scenario fixtures
- Files removed: `src/game/engine/simulation.py`, `tests/engine/test_simulation.py`
- Tests added: VillaUpdate validation, movement application, background conversation start/close, hash exclusion for NPC-NPC dialogue, mock and live agent contract tests
- QA result: Make is not installed in this PowerShell session, so the Makefile targets were run directly: `ruff`, `mypy`, `content lint`, non-LLM pytest, smoke replay, fixture determinism all green; 68 non-LLM tests passed; Orchestrator and Background Dialogue LLM subsets green, 2 LLM tests passed
- Scenario fixture: existing fixtures regenerated for schema v9 and empty mock VillaUpdate commits

## Phase G4 replay wiring

- Files added: `src/game/engine/recorded_agents.py`
- Files changed: `src/game/cli/commands/play.py`, `src/game/agents/conversation_curator.py`
- Tests added: manual CLI smoke for `play --mock-llm --record` followed by `play --replay` on the generated trace
- QA result: `ruff`, `mypy`, non-LLM pytest, content lint green; recorded mock playthrough replayed to the same final hash; full LLM suite green, 28 tests passed
- Scenario fixture: unchanged

## Phase G6

- Files added: `review-packet/session.html`, `review-packet/artifacts/session.json`, `review-packet/artifacts/session-trace.json`
- Files changed: `src/game/cli/commands/report.py`, `src/game/reporting/html.py`, `src/game/agents/contextual_options.py`, `tests/agents/test_contextual_options.py`, `review-packet/index.html`, `review-packet/notes.md`, `review-packet/how-to-reproduce.md`
- Files removed: policy script fixtures and the old multi-session/balance/narration-quality packet files
- Tests added: non-LLM test proving the Contextual Options runtime preserves exactly one exit wheel option; manual CLI smoke for `report packet --trace` and `report from-trace`; trace replay confirmed the generated live recording reproduces the same final hash
- QA result: `ruff`, `mypy`, non-LLM pytest, content lint, smoke replay, fixture determinism all green; full LLM suite green, 28 tests passed
- Packet: regenerated from `.game_traces/live-recording.json` at `review-packet/index.html`

## Phase G7

- Files added: `tests/cli/test_play.py`
- Files changed: `src/game/cli/commands/play.py`, `src/game/engine/rules.py`, `src/game/reporting/html.py`, `tests/engine/test_rules.py`, `tests/engine/test_gossip.py`, `review-packet/`
- Tests added: CLI villa map rendering, detailed villa update rendering, risk-based follow-up success caps
- QA result: `ruff`, `mypy`, non-LLM pytest green; manual trace replay still reproduces the same final hash after the balance change
- Packet: regenerated from `.game_traces/manual-day1.json` at `review-packet/index.html`

## Phase G8.1

- Files added: none
- Files changed: `src/game/engine/intents.py`, `src/game/engine/rules.py`, `src/game/engine/turn.py`, `src/game/engine/actions.py`, `src/game/cli/commands/play.py`, `src/game/engine/conversation.py`, `tests/engine/test_rules.py`, `tests/engine/test_turn.py`, scenario fixtures
- Tests added: initial intent risk caps, explicit intent risk override, wheel exit closes and grants trust, walk-away closes and applies affection penalty
- QA result: `ruff`, `mypy`, non-LLM pytest, content lint, smoke replay, fixture determinism all green
- Scenario fixture: `conversation-multi-exchange.yaml` and `day1-full-stats.yaml` regenerated after exit semantics and intent caps

## Phase G8.2

- Files added: `src/game/engine/pull.py`, `tests/engine/test_pull.py`, `tests/agents/test_islander_voice_pull_rejected.py`
- Files changed: `src/game/engine/rules.py`, `src/game/engine/turn.py`, `src/game/agents/islander_voice.py`, `src/game/cli/commands/play.py`, `src/game/reporting/html.py`
- Tests added: pull chance factors and clamps, contested pull success/failure, pull rejection memories, pull attempt trace fields, pull-rejection Islander Voice contracts
- QA result: `ruff`, `mypy`, non-LLM pytest, content lint, fixture determinism all green; pull-rejection LLM subset green, 4 tests passed
- Scenario fixture: unchanged

## Phase G8.3

- Files added: `tests/engine/test_interruptions.py`, `tests/agents/test_villa_orchestrator_interruptions.py`
- Files changed: `src/game/state/models.py`, `src/game/agents/villa_orchestrator.py`, `src/game/engine/actions.py`, `src/game/engine/rules.py`, `src/game/engine/turn.py`, `src/game/engine/villa.py`, `src/game/cli/commands/play.py`, scenario fixtures
- Tests added: VillaUpdate interruption validation, pending interruption wheel injection, welcome/defer/ignore mechanics and memories, Orchestrator interruption contract contexts
- QA result: `ruff`, `mypy`, non-LLM pytest, content lint, fixture determinism all green; Orchestrator interruption LLM subset green, 5 tests passed
- Scenario fixture: existing fixtures regenerated for schema v10 and pending interruption state shape

## Phase G8.4

- Files added: `src/game/eval/__init__.py`, `src/game/eval/playthrough.py`, `tests/eval/test_playthrough.py`
- Files changed: `src/game/cli/commands/verify.py`
- Tests added: playthrough report assertion count, complete-trace pass, missing pull failure, memory holder coverage, interesting turn sorting
- QA result: `ruff`, `mypy`, non-LLM pytest, content lint, fixture determinism all green; manual `verify --playthrough .game_traces/manual-day1.json` produced a structured report with 4/11 assertions passing for the old recording
- Scenario fixture: unchanged
