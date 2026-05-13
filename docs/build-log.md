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

## Phase G8.5

- Files added: `src/game/reporting/eval_dashboard.py`, `tests/reporting/test_html.py`, `review-packet/playthrough-eval.html`
- Files changed: `src/game/reporting/html.py`, `src/game/cli/commands/play.py`, `src/game/cli/commands/report.py`, `tests/agents/test_islander_voice_pull_rejected.py`, `review-packet/`
- Tests added: session HTML exposes success math, villa snapshots, memories, pulls, interruptions; eval dashboard links assertions back to session turns
- QA result: `ruff`, `mypy`, non-LLM pytest, content lint, fixture determinism all green; full LLM suite green, 37 tests passed; packet regenerated and verified in the in-app browser at `http://127.0.0.1:8895/review-packet/index.html`
- Packet: regenerated from `.game_traces/manual-day1.json`; dashboard shows the old recording passes 4/11 playthrough assertions, which is expected until the next G8-aware recorded session is played

## Phase G8 review polish

- Files added: none
- Files changed: `.gitignore`, `src/game/engine/rules.py`, `src/game/agents/contextual_options.py`, `src/game/eval/playthrough.py`, `src/game/reporting/eval_dashboard.py`, `src/game/reporting/html.py`, tests, `review-packet/`
- Tests added: chance breakdown formula terms, idempotent recorded gossip menu replay, ceremony assertion coverage, stricter interruption response-kind coverage, rendered formula breakdown text
- QA result: `ruff`, `mypy`, non-LLM pytest, content lint, fixture determinism, trace replay, and full LLM suite all green; fresh G8 trace passes 11/11 playthrough assertions
- Packet: regenerated from `.game_traces/manual-g8.json`; in-app browser verified `session.html` includes formula breakdowns and `playthrough-eval.html` shows 11 passed / 0 failed

## Phase G9 cleanup

- Files added: focused rule/render helper modules for chance math, follow-ups, gossip, interruptions, perception, results, state access, CLI play rendering, and HTML rendering
- Files changed: `src/game/engine/rules.py`, `src/game/cli/commands/play.py`, `src/game/reporting/html.py`, CLI dispatch, Makefile, QA/docs references, and review-packet notes/session disclosure
- Files removed: abandoned tool-boundary stub, unused CLI scaffold commands, stale snapshot/trace fixtures, hollow `scripts/fixtures/`, and duplicate ceremony design doc
- Tests added: none; cleanup keeps existing behavior and coverage
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, non-LLM pytest, content lint, smoke `verify-script`, fixture determinism, trace replay, playthrough eval, packet regeneration, and full LLM suite all green
- Packet: regenerated from `.game_traces/manual-g8.json`; session report now discloses mock-LLM mode and in-app browser verified review surfaces

## Phase H1

- Files added: `src/game/engine/character_creation.py`, `src/game/engine/audience.py`, `src/game/engine/final_vote.py`, player archetype content, audience/final-vote tests, and two H1 scenario fixtures
- Files changed: state models, action/rule/turn pipelines, scenario replay, CLI play/report rendering, content loading/linting, eval dashboard/assertions, and all scenario hashes for schema v11
- Tests added: character creation validation and starter advantages, audience ranking/scoring, final vote outcomes/events, H1 playthrough eval assertions, and character/final-vote scenario fixtures
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, non-LLM pytest (127 passed), content lint, smoke `verify-script`, fixture determinism, and full LLM suite (37 passed)
- Scenario fixture: all fixtures regenerated for `SCHEMA_VERSION = 11`; new `character-creation.yaml` and `day6-final-vote.yaml` pin the start and end of the run

## Phase H2

- Files added: deterministic challenge and producer-event engines, event state models, challenge/producer content, event HTML helpers, challenge/producer tests, and two H2 scenario fixtures
- Files changed: state schema, turn/action/rule pipelines, content loading/linting, CLI/report rendering, snapshot hashing, playthrough eval/dashboard, and all scenario hashes for schema v12
- Tests added: daily challenge scheduling/resolution, producer text scheduling/group-date setup, H2 eval assertions, and `challenge-day1.yaml` / `producer-text-day2.yaml`
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, non-LLM pytest (145 passed), content lint, smoke `verify-script`, fixture determinism, and full LLM suite (37 passed)
- Scenario fixture: all fixtures regenerated for `SCHEMA_VERSION = 12`; long day-five-plus fixtures now include the required `CHALLENGE_RESPONSE` for Snog Marry Pie

## Phase H3

- Files added: `src/game/state/personality.py`, `src/game/engine/compatibility.py`, `src/game/eval/playthrough_trace.py`, `tests/engine/test_compatibility.py`, and `tests/scenarios/fixtures/type-on-paper-reveal.yaml`
- Files changed: islander state schema, bombshell setup, chance/rule/follow-up math, conversation familiarity updates, Islander Voice context, CLI/report rendering, playthrough eval/dashboard, and all scenario hashes for schema v13
- Tests added: Big 5 / attachment / Type on Paper model checks, compatibility/dealbreaker/attachment modifiers, familiarity/reveal thresholds, compatibility math in rules, H3 playthrough eval assertions, and the Type-on-Paper reveal fixture
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, non-LLM pytest (160 passed), content lint, smoke `verify-script`, fixture determinism, and full LLM suite (37 passed)
- Scenario fixture: all fixtures regenerated for `SCHEMA_VERSION = 13`; `type-on-paper-reveal.yaml` pins familiarity-driven preference reveals

## Phase H4

- Files added: `src/game/engine/couples.py`, `src/game/engine/hideaway.py`, `content/locations/hideaway.md`, `tests/engine/test_couples.py`, `tests/engine/test_hideaway.py`, and `tests/scenarios/fixtures/hideaway-night.yaml`
- Files changed: state schema, action/rule/turn-event pipelines, recoupling ceremony events, audience scoring, CLI/report recording/rendering, playthrough eval/dashboard, scenario runner initial-state support, and all scenario hashes for schema v14
- Tests added: couple strength/ranking/steal math, Hideaway eligibility/consumption/deltas/memories, H4 eval assertions, and the Hideaway night fixture
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, non-LLM pytest (176 passed), content lint, smoke `verify-script`, fixture determinism, and full LLM suite (37 passed)
- Scenario fixture: all fixtures regenerated for `SCHEMA_VERSION = 14`; `hideaway-night.yaml` pins the once-per-run Hideaway reward

## Phase H6

- Files added: stylish reporting package (`css.py`, `avatars.py`, `timeline.py`, `couple_status.py`, `perception_graph.py`), `src/game/reporting/memory_web.py`, and `tests/reporting/test_stylish.py`
- Files changed: session report rendering, packet/report CLI minimal fallback flag, eval dashboard styling, and regenerated review packet HTML
- Tests added: stylish session self-containment, deterministic avatars, day timeline markers, couple status panel, perception graph, memory web edge filtering/styles, final-outcome preface, and collapsed math details
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, non-LLM pytest (189 passed), content lint, smoke `verify-script`, fixture determinism, and full LLM suite (37 passed)
- Packet: regenerated from `.game_traces/manual-g8.json`; in-app browser verified `session.html` exposes the H6 layout, day nav, couple panel, public perception graph, memory web, turn cards, and math details

## Phase H5

- Files added: `src/game/state/casa.py`, `src/game/engine/casa_amor.py`, Casa Amor locations, six Casa Amor cast content files, `content/producer_texts/casa_amor_announce.md`, `src/game/reporting/html_math.py`, `tests/engine/test_casa_amor.py`, and two Casa scenario fixtures
- Files changed: state schema, action/rule/turn-event pipelines, villa orchestration validation/context, CLI/report recording/rendering, content loading/linting, playthrough eval/dashboard, H-index fixture list, and all scenario hashes for schema v15
- Files removed: stale day-four bombshell producer text and `bombshell-day4.yaml` fixture now superseded by Casa Amor arrival
- Tests added: Casa entry/cast/location/menu/decision/return/perception/orchestrator-visibility checks, Casa eval assertions, and `casa-amor-arrive.yaml` / `casa-amor-return.yaml`
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, non-LLM pytest (203 passed), content lint, smoke `verify-script`, fixture determinism, line-cap audit, and full LLM suite (37 passed)
- Scenario fixture: all fixtures regenerated for `SCHEMA_VERSION = 15`; day-five-plus fixtures now include the required Casa Amor decision before the day-six return

## Phase H7

- Files added: `src/game/agents/player_autopilot.py`, `src/game/agents/prompts/player_autopilot.md`, `src/game/cli/commands/play_autopilot.py`, `src/game/cli/commands/play_recording.py`, `tests/agents/test_player_autopilot.py`, and `tests/scenarios/fixtures/autopilot-day1.yaml`
- Files changed: CLI play/report recording surfaces, agent commit schema, scenario replay, playthrough eval/dashboard, contextual follow-up mechanics, background dialogue validation, pull-for-chat Casa location support, and Makefile `autopilot-check`
- Tests added: Player Autopilot LLM contract tests, mock autopilot end-to-end/replay/rationale tests, supportive follow-up delta coverage, background-dialogue validator retry coverage, Casa pull-location coverage, and autopilot scenario fixture
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, non-LLM pytest (218 passed), content lint, fixture determinism, line-cap audit, and full LLM suite (43 passed)
- Validation note: fast deterministic `autopilot-check` completes and replays byte-identically; bounded real-LLM validation exposed phase-pacing gaps that are addressed by Phase H8 time budgets and NPC autonomy

## Phase H8.1

- Files added: `docs/build-plan-H8.md`, `src/game/state/phase_clock.py`, `src/game/engine/time_budget.py`, `tests/engine/test_time_budget.py`, and `tests/scenarios/fixtures/time-budget-expiry.yaml`
- Files changed: state schema, phase advancement, turn pipeline, scenario replay setup, CLI/report time rendering, playthrough eval/dashboard, and all scenario hashes for schema v16
- Tests added: action time-cost contract, time deduction expiry, phase-clock reset, run-turn auto-advance, H8 pacing eval assertions, and a time-budget expiry scenario fixture
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, non-LLM pytest (223 passed), content lint, smoke `verify-script`, fixture determinism, line-cap audit, and full LLM suite (43 passed after one retry of a stochastic pre-existing voice-quality assertion)
- Scenario fixture: all fixtures regenerated for `SCHEMA_VERSION = 16`; day-five Casa fixtures remove one manual `ADVANCE_PHASE` because challenge responses now auto-advance zero-budget challenge phases

## Phase H8.2

- Files added: `src/game/engine/arrival_rolls.py`, `src/game/engine/turn_autonomy.py`, `src/game/eval/playthrough_models.py`, `src/game/reporting/html_arrivals.py`, `src/game/state/autonomy.py`, `tests/engine/test_arrival_rolls.py`, `tests/engine/test_npc_summoned.py`, and two scenario fixtures for arrival rolls and summoned exits
- Files changed: Villa Orchestrator schema/prompt, VillaUpdate validation/application, turn autonomy pipeline, conversation departure math, trace recording, CLI/report rendering, playthrough eval/dashboard, scenario replay scripted VillaUpdates, and all scenario hashes
- Tests added: arrival roll formulas/clamps/breakdown, NPC summon validation/application/curation/movement, attachment-driven departure modifiers, H8 autonomy eval assertions, scripted VillaUpdate replay, `arrival-roll-interrupt.yaml`, and `npc-summoned-exit.yaml`
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, non-LLM pytest (235 passed), content lint, smoke `verify-script`, fixture determinism, line-cap audit, and full LLM suite (43 passed)
- Prompt note: installed Claude's `villa_orchestrator.md` NPC summoning section verbatim after `## Hard rules`; no other prompt edits made

## Phase H8.3

- Files added: `tests/conftest_test.py` for test infrastructure checks and `pytest-xdist` / `execnet` in the lockfile
- Files changed: `Makefile`, `pyproject.toml`, `uv.lock`, `tests/conftest.py`, OpenAI-backed agent classes, CLI autopilot tests, playthrough eval/dashboard, and QA docs
- Tests added: session-scoped content-index fixture coverage, lazy OpenAI client construction check, pytest-xdist availability check, stalled day-progression assertion coverage, and faster in-process CLI autopilot replay tests
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, parallel non-LLM pytest via xdist (239 passed in 8.41s), content lint, smoke `verify-script`, fixture determinism, line-cap audit, `pytest --durations=20` max test 0.13s, and full LLM suite (43 passed)
- Performance note: `make test` now runs `pytest -m "not llm" -n auto`; `test-fast` runs engine tests in parallel; OpenAI clients are constructed lazily on first real agent call

## Phase H8 Validation Hardening

- Files changed: Player Autopilot persona setup, Villa Orchestrator context/retry handling, Conversation Curator context/retry handling, VillaUpdate normalization, and focused regression tests
- Tests added: legal 30-point persona stat coverage, required curator-memory-holder context coverage, locked NPC conversation context coverage, and implicit conversation-end normalization for moved or stale-location NPC conversations
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, parallel non-LLM pytest via xdist (244 passed in 8.60s), content lint, smoke `verify-script`, fixture determinism, line-cap audit, and full LLM suite (43 passed)
- Validation result: real-LLM loyal validation recorded 61 turns, reached Day 5, and passed H8-specific acceptance signals; real-LLM chaotic validation recorded 83 turns, reached Day 6, and passed H8-specific acceptance signals
- Packet: generated `review-packet-loyal/` and `review-packet-chaotic/` from `.game_traces/h8-validation-loyal.json` and `.game_traces/h8-validation-chaotic.json`

## Phase H8 Packet Eval Fix

- Files changed: report packet/eval-dashboard generation now preserves trace `mode` and `persona` when evaluating recorded traces
- Tests added: packet command regression proving an autopilot trace is not evaluated as a manual trace in `playthrough-eval.html`
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, parallel non-LLM pytest via xdist (245 passed in 9.67s), content lint, smoke `verify-script`, fixture determinism, and full LLM suite (43 passed)
- Packet: regenerated `review-packet-loyal/` and `review-packet-chaotic/`; both dashboards now match `verify --playthrough` at 24 passed / 7 failed

## Phase H9.1

- Files added: `docs/build-plan-H9.md` and `src/game/state/memory.py`
- Files changed: canonical state gender schema, character creation, intent filtering, intent catalog, Islander Voice context/prompt, Casa/bombshell cast creation, CLI character card, scenario replay, and all scenario hashes for `SCHEMA_VERSION = 17`
- Tests added: required character-creation gender, canonical cast gender assignment, same/opposite-sex intent filtering, bromance/gossip-ring mechanical deltas, and Islander Voice LLM coverage for the expanded intent catalog
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, parallel non-LLM pytest via xdist (253 passed in 10.53s), content lint, smoke `verify-script`, fixture determinism, line-cap audit, and full LLM suite (51 passed)
- Scenario fixture: all fixtures regenerated for `SCHEMA_VERSION = 17`; `character_creation` and `CREATE_CHARACTER` payloads now include the required gender field

## Phase H9.2

- Files added: `content/archetypes/alpha.md`, `src/game/state/cast.py`, and `tests/engine/test_initial_coupling.py`
- Files changed: starting cast factory, initial coupling action flow, recoupling ceremony handling, content lint expectations, Islander Voice known-name set, audience/model tests, and all scenario hashes for the expanded starting cast
- Tests added: eight-islander starting cast, four-men/four-women gender balance, day-one initial coupling options, initial coupling without day-one dumping, and four-couple audience rankings
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, parallel non-LLM pytest via xdist (258 passed in 10.96s), content lint, smoke `verify-script`, fixture determinism, line-cap audit, and full LLM suite (51 passed)
- Scenario fixture: all fixtures regenerated after the cast expansion; pre-created-character fixtures now pin initial couples so they do not block on the new day-one coupling menu

## Phase H9.3

- Files added: `content/backstories.yaml`
- Files changed: Islander state schema, content loading/linting, starting/Casa/bombshell cast factories, Islander Voice context/prompt, Contextual Options context/prompt, and all scenario hashes for `SCHEMA_VERSION = 18`
- Tests added: per-islander backstory loading, Islander Voice backstory context coverage, Islander Voice meta-talk rejection, and Contextual Options specificity checks
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, parallel non-LLM pytest via xdist (260 passed in 9.61s), content lint, fixture determinism, line-cap audit, and full LLM suite (53 passed)
- Scenario fixture: all fixtures regenerated for backstory-bearing islander state

## Phase H9.4

- Files added: none
- Files changed: player state pull-attempt tracking, pull chance math, phase reset behavior, interruption response mechanics, mechanical result trace schema, and all scenario hashes for `SCHEMA_VERSION = 19`
- Tests added: repeated pull chance penalty, minimum pull clamp after repeated attempts, phase reset for pull attempts, repeated-pull memory creation, ignored-interruption walkaway movement, and forced movement trace coverage
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, parallel non-LLM pytest via xdist (266 passed in 9.31s), content lint, smoke `verify-script`, fixture determinism, line-cap audit, and full LLM suite (53 passed)
- Scenario fixture: all fixtures regenerated for pull-attempt tracking and forced-movement trace schema

## Phase H9.5

- Files added: `content/locations/firepit.md`, `src/game/engine/gather.py`, `src/game/engine/pull_turn.py`, and `src/game/reporting/html_gather.py`
- Files changed: canonical state schema, action validation/surfacing, time budgets, phase event scheduling, turn pipeline, CLI/report rendering, Casa location set, and all scenario hashes for `SCHEMA_VERSION = 20`
- Tests added: producer-text gather scheduling, Casa Amor gather resolution, conversation cleanup before gather events, final vote gather resolution, and updated Casa/final-vote tests for the two-step schedule/resolve flow
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, parallel non-LLM pytest via xdist (268 passed in 12.04s), content lint, smoke `verify-script`, fixture determinism, line-cap audit, and full LLM suite (53 passed)
- Scenario fixture: all fixtures regenerated for mandatory gather events; scripts now include `join_gather` where producer texts or ceremonies must interrupt normal play

## Phase H9.6

- Files added: `src/game/engine/daily_recap.py` and `src/game/reporting/stylish/background.py`
- Files changed: canonical state schema, state hash exclusions, turn day-rollover recap generation, CLI slash-command handling, trace recording, stylish report rendering, and all scenario hashes for `SCHEMA_VERSION = 21`
- Tests added: `/background` history rendering, full background-dialogue HTML rendering, daily recap generation at day rollover, and daily recap prose hash exclusion
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, parallel non-LLM pytest via xdist (272 passed in 10.06s), content lint, fixture determinism, line-cap audit, and full LLM suite (53 passed on rerun after one stochastic pre-existing pull-rejection wording failure)
- Scenario fixture: all fixtures regenerated for daily recap state

## Phase H9.7

- Files added: none
- Files changed: Villa Orchestrator movement prompt, Orchestrator context rendering, VillaUpdate validation during pending gathers, and related tests
- Tests added: isolated-player context coverage, pending-gather autonomy rejection, Firepit pull privacy coverage, and two LLM tests for H9.7 movement liveliness
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, parallel non-LLM pytest via xdist (274 passed in 10.36s), content lint, fixture determinism, line-cap audit, H9.7 focused LLM suite (3 passed), and full LLM suite (55 passed after increasing the command timeout)
- Prompt note: installed Claude's H9.7 `villa_orchestrator.md` movement bullet verbatim; no other prompt edits made

## Phase H9.7: fix gather autonomy pause

- Files added: none
- Files changed: `turn_autonomy.py`, `test_turn.py`
- Tests added: coverage that the turn scheduling a mandatory gather does not invoke Villa Orchestrator
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, parallel non-LLM pytest via xdist (276 passed), smoke script, content lint, fixture determinism, and line-cap audit
- Validation note: fixes the H9 real-LLM autopilot crash where an Orchestrator movement was rejected after `ADVANCE_PHASE` scheduled a pending gather

## Phase H9.7: accept public names in event narration validation

- Files added: none
- Files changed: `event_narrator.py`, `test_event_narrator.py`
- Tests added: coverage that starting-cast ids such as `jordan_start` satisfy event narration validation when prose names the public first name
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, parallel non-LLM pytest via xdist (277 passed), smoke script, content lint, fixture determinism, line-cap audit, and focused Event Narrator suite
- Validation note: fixes the H9 real-LLM autopilot crash where the narrator wrote `Jordan` for internal id `jordan_start`

## Phase H9.7: retry Islander Voice contract failures

- Files added: none
- Files changed: `islander_voice.py`, `test_islander_voice.py`
- Tests added: coverage that Islander Voice retries after a validation failure and feeds the failure reason into the next structured call
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, parallel non-LLM pytest via xdist (278 passed), smoke script, content lint, fixture determinism, line-cap audit, and focused Islander Voice retry coverage
- Validation note: fixes the H9 real-LLM autopilot crash where Islander Voice returned a valid schema with digit-bearing prose

## Phase H10.1

- Files added: `src/game/agents/islander_voice_context.py`, `tests/agents/test_islander_voice_chain.py`
- Files changed: Islander Voice now sends prior conversation exchanges as native OpenAI messages, the Islander Voice prompt installs Claude's recent-history line replacement verbatim, and Islander Voice stays under the R9 line cap after helper extraction
- Tests added: first-exchange message shape, prior exchange alternating user/assistant message shape, prior assistant JSON validation, and current-turn intent/outcome context coverage
- QA result: direct `make qa` equivalents green because `make` is unavailable in this PowerShell session: `ruff`, `mypy`, parallel non-LLM pytest via xdist (281 passed), smoke script, content lint, fixture determinism, line-cap audit, focused Islander Voice chain tests, and LLM suite rerun note: one stochastic pull-rejection wording miss passed on focused rerun
- Prompt note: installed Claude's H10.1 `islander_voice.md` recent-history line replacement verbatim; no other prompt edits made
