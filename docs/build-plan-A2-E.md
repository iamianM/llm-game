# Build Plan: Phases A2 through E

> Historical build plan. This file is kept for implementation context only.
> Current planning lives in [current-plan.md](current-plan.md).

Superseded by later Phase G and G8 work. This file is historical context only; use current Makefile targets, `docs/build-plan-G.md`, and `docs/build-plan-G8.md` for active implementation details.

This is the hand-off document Codex executes against to take the game from the Phase A1 starting slice to a reviewable v0. Read [`ENGINEERING.md`](../ENGINEERING.md), [`docs/qa-strategy.md`](qa-strategy.md), and every ADR in [`docs/decisions/`](decisions/) before each phase.

The phases ship in order. Each ends with `make qa` green, new tests, a checked-in scenario fixture with `expected_hash`, and a single git commit. The user reviews the final packet at the end of Phase E; the rest is autonomous.

---

## Operating Contract

1. **Read first.** Before every phase: re-read `ENGINEERING.md`, the ADR index, this plan, and the design docs cited in that phase's section.
2. **Smallest complete change.** Make the change. Add tests that protect the contract touched. Run `make qa`. If anything fails, fix root cause (R5) — no `# type: ignore`, no `--no-verify`.
3. **Commit at phase end.** One commit per phase, message format: `Phase <id>: <one-line summary>`. Append a 5-line entry to `docs/build-log.md` (create on first use): phase name, files added, tests added, qa result, scenario fixture name. The build log is append-only; never edit prior entries.
4. **Continue without permission.** If a phase's acceptance criteria are met, move directly to the next phase. Do not ask the user to confirm. Stop and report only if:
   - A phase takes more than 2 sessions.
   - `make qa` is red and you cannot fix it.
   - You are about to exceed the LLM budget cap.
   - The scope changes (you would need to do something the plan does not authorize).
5. **Mid-plan checkpoint.** After Phase B commits, run `make play` through one full 6-day session with mock narration, save it as `review-packet-preview/session-phaseB.html` via a temporary minimal renderer, and post the path to the user. This is the only mandatory interim report. Continue to Phase C while waiting.
6. **Final report.** End of Phase E: produce the review packet under `review-packet/` and post the path. Done.

---

## Phase A1 Closeout (do this before A2)

Tidy the last commit before starting A2. Estimated 15 minutes.

- Add [`tests/engine/test_models.py`](../tests/engine/test_models.py): `test_game_state_forbids_extra_fields`, `test_clamp_relationship_boundaries`, `test_save_load_roundtrip_preserves_hash` (uses `tmp_path`).
- Add `test_state_hash_is_stable_across_dumps` to the same file.
- Add `test_apply_action_does_not_bump_turn_index` to [`tests/engine/test_turn.py`](../tests/engine/test_turn.py).
- Move `_mock_narration` from [`src/game/engine/turn.py`](../src/game/engine/turn.py) to [`src/game/agents/narrator.py`](../src/game/agents/narrator.py) as `mock_narration(state, result) -> str`; import it back into turn.py. Keeps R15 boundary clean.
- Delete [`scripts/fixtures/day1-happy-path.yaml`](../scripts/fixtures/) and point the `smoke` Makefile target at `tests/scenarios/fixtures/day1-happy-path.yaml`. One source of truth.
- Change `docs/qa-strategy.md` line that says `"intended non-LLM gate"` to `"current non-LLM gate"`.
- Annotate the in-session slash command list in [`AGENTS.md`](../AGENTS.md) as `implemented in A1` vs `planned`.
- `make qa` green. Commit: `Phase A1 closeout: cover snapshot, models, mutation invariants`.

---

## Phase A2: Flirt and Chemistry

**Design source:** [02-Core-Mechanics.md](../02-Core-Mechanics.md) (Interaction Success Formula, Relationship Stats), [05-Interaction-System.md](../05-Interaction-System.md) (Hybrid Menu System).

**Scope.** Add the FLIRT action with real success math. Add Chemistry as a relationship value.

**Changes.**
- [`state/models.py`](../src/game/state/models.py): add `chemistry: int = Field(default=0, ge=0, le=100)` to `RelationshipState`. Bump `SCHEMA_VERSION` to 2; regenerate fixture hashes; delete old hashes (R12).
- [`engine/actions.py`](../src/game/engine/actions.py): `available_actions` returns FLIRT for each visible islander alongside TALK.
- [`engine/rules.py`](../src/game/engine/rules.py): add `_apply_flirt` with formula `chance = 40 + charm*5 + chemistry//4`, clamped `[5, 95]`. Success: chemistry +5, affection +2, tag `flirty`. Miss: chemistry -1, no affection change, tag `awkward`. Hardcoded deltas become named module-level constants.
- [`engine/rules.py`](../src/game/engine/rules.py): promote `MechanicalResult.relationship_deltas` from `dict[str, dict[str, int]]` to `dict[str, RelationshipDelta]` where `RelationshipDelta` is a Pydantic model with `affection: int = 0, chemistry: int = 0`. Prevents typo'd stat names (R10).
- [`cli/commands/play.py`](../src/game/cli/commands/play.py): no change required — `available_actions` drives the menu.
- New fixture: `tests/scenarios/fixtures/day1-flirt-mixed.yaml` with at least one FLIRT, one TALK, one ADVANCE_PHASE, and an `expected_hash`. Include a comment showing the regeneration command.

**Acceptance criteria.**
- `make qa` green.
- `make play` shows both `Talk to X` and `Flirt with X` for each islander.
- `tests/engine/test_rules.py` has new tests: `test_flirt_success_bumps_chemistry`, `test_flirt_miss_drops_chemistry`, `test_relationship_delta_rejects_unknown_field` (asserts Pydantic `extra="forbid"`).
- Both `day1-happy-path.yaml` and `day1-flirt-mixed.yaml` are verified by `make determinism`.

**Anti-goals.** Do not add LISTEN or LEAVE in this phase. Do not gate FLIRT behind a stat threshold yet — that's A3. Do not vary the formula per archetype yet.

---

## Phase A3: Full Stats and Remaining Actions

**Design source:** [02-Core-Mechanics.md](../02-Core-Mechanics.md) (Player Stats, Stat Gating), [00-Game-Start-And-Setup.md](../00-Game-Start-And-Setup.md) (Stat Allocation, 30-point budget).

**Scope.** Fill out the 5-stat surface. Add LISTEN and LEAVE. Implement stat gating.

**Changes.**
- [`state/models.py`](../src/game/state/models.py): expand `PlayerStats` to all five — `charm, banter, eq, graft, loyalty`, each `ge=3, le=9`. Add `model_validator` ensuring total ≤ 30. Bump `SCHEMA_VERSION` to 3.
- `state/models.py`: extend `RelationshipState` to include `trust: int = Field(default=0, ge=0, le=100)` and `friendship: int = Field(default=0, ge=0, le=100)`.
- [`engine/actions.py`](../src/game/engine/actions.py): add LISTEN and LEAVE to `available_actions`. Add a `min_stat: tuple[str, int] | None = None` field on `ActionSpec`. `available_actions` filters out specs whose `min_stat` requirement is unmet.
- [`engine/rules.py`](../src/game/engine/rules.py): `_apply_listen` uses EQ + Affection, adds `trust +3` on success, `friendship +1` always. `_apply_leave` exits cleanly with `tag=["disengaged"]` and no deltas. Add a `BOLD` flirt variant unlocked at `graft >= 5` per [02-Core-Mechanics.md](../02-Core-Mechanics.md); higher reward, higher risk.
- `cli/commands/play.py`: menu rendering picks up the new actions automatically. Show the stat requirement next to gated options: `Flirt boldly with Chloe (Graft 5)`.
- New fixture: `tests/scenarios/fixtures/day1-full-stats.yaml` exercising all five action kinds. Add a second fixture `day1-low-stats.yaml` where gated options are absent (player with graft=3) and the fixture's actions cannot include BOLD flirt — `make determinism` proves the gate works.

**Acceptance criteria.**
- `make qa` green.
- All 5 stats in `PlayerStats`. Total budget validator works (reject `model_validate` with sum > 30).
- LISTEN, LEAVE, BOLD flirt visible in `make play` when stat thresholds are met; absent otherwise.
- `tests/engine/test_actions.py` has `test_bold_flirt_locked_below_graft_5` and `test_bold_flirt_unlocked_at_graft_5`.

**Anti-goals.** No archetype-specific mechanics yet (A3 is purely player-side). No personality (Big 5) modeling on NPCs yet — that's Phase D's prompt input only. No "Type on Paper" preference matching yet.

---

## Phase B: Multi-Day and NPC Simulation

**Design source:** [08-Daily-Loop.md](../08-Daily-Loop.md), [06-Location-System.md](../06-Location-System.md), [09-Social-Dynamics.md](../09-Social-Dynamics.md).

**Scope.** Extend from one day to a 6-day run. Add locations. NPCs move and interact autonomously between player turns.

**Changes.**
- [`state/models.py`](../src/game/state/models.py): `Day` advances when phase wraps from EVENING back to MORNING. Track `current_day: int = 1`. Terminal state is `day > 6` (configurable constant). Add `Location` enum: `POOL, KITCHEN, TERRACE, BEDROOM`. Each `IslanderState.location_id` references a `Location`.
- [`engine/phases.py`](../src/game/engine/phases.py): phase progression includes day rollover. Add a per-phase RNG fork: `rng.fork(f"day-{day}-phase-{phase}")` so NPC simulation in each phase is reproducible and independent.
- New module `engine/simulation.py`: `simulate_off_screen(state, rng) -> list[OffScreenEvent]`. Called when player advances phase. NPCs at the player's location may or may not move based on extraversion-proxy (deterministic from archetype). NPCs at other locations interact pairwise based on chemistry, producing relationship updates among themselves. Player only sees aggregate visible-state changes, not the prose of NPC-NPC interactions. `OffScreenEvent` is a Pydantic model: `actor_id, target_id, kind, location`.
- [`cli/commands/play.py`](../src/game/cli/commands/play.py): add location selector — player can move between locations during certain phases (MORNING, AFTERNOON). Action `MOVE` to `Location`. Player's location filters which islanders are visible.
- Add `archetype` → behavior table in `engine/simulation.py`. Three archetypes for now: `sweetheart, joker, friend` (matches A1 cast). Each has fixed `move_propensity` and `flirt_propensity` constants.
- New fixture: `tests/scenarios/fixtures/day6-full-run.yaml` — 6 days, mix of TALK/FLIRT/LISTEN/MOVE/ADVANCE_PHASE. Verify final hash.

**Acceptance criteria.**
- `make qa` green.
- `make play` plays 6 days end-to-end without crashes.
- `simulate_off_screen` is fully deterministic: same seed + same player actions = same NPC-NPC interaction sequence. Test `test_off_screen_simulation_deterministic_under_replay` proves it.
- Player at a different location sees a filtered visible state (other-location islanders not in menu).
- Mid-plan checkpoint: produce a minimal HTML render of one full 6-day session under `review-packet-preview/session-phaseB.html`. Post path to user. Continue to C.

**Anti-goals.** No bombshells, no recouplings, no eliminations — those are Phase C. No real LLM. No new archetypes beyond the three. No event system for "I've Got a Text" — that's Phase C. Off-screen NPC interactions produce mechanical updates only, no narration.

---

## Phase C: Couples, Recoupling, Elimination

**Design source:** [10-Elimination-System.md](../10-Elimination-System.md), [12-Challenges-And-Events.md](../12-Challenges-And-Events.md) (only the recoupling and bombshell parts; no challenges yet).

**Scope.** Players and NPCs form couples. Day-end recoupling ceremony reshuffles them. Bombshells arrive. Public Perception tracks. Player can be eliminated.

**Changes.**
- [`state/models.py`](../src/game/state/models.py): add `Couple` Pydantic model with `partner_a_id, partner_b_id, formed_on_day`. Add `couples: list[Couple]` to `GameState`. Add `public_perception: int = Field(default=50, ge=0, le=100)` to `IslanderState` and `PlayerState`. Add `eliminated: bool = False` to islander and player.
- [`engine/ceremonies.py`](../src/game/engine/) (new module): `recoupling(state, rng) -> RecouplingResult` runs end-of-day-3 and end-of-day-5. Algorithmic choice per islander: pick partner with highest `affection + chemistry/2`. Player chooses interactively in `play.py`. Unpartnered islander after recoupling is eliminated.
- `engine/ceremonies.py`: `arrive_bombshell(state, rng) -> Islander` adds a new islander mid-run on day 4. Bombshell has high baseline chemistry with random existing islanders to force drama.
- `engine/rules.py`: public_perception updates per action (loyalty actions raise it, "snakey" patterns lower it). `update_public_perception(state, action, result)` runs after every `apply_action`.
- `cli/commands/play.py`: recoupling prompt presented at the right phase. Bombshell arrival announced. Elimination ends the run with a clear screen.
- New fixtures: `tests/scenarios/fixtures/recoupling-day3.yaml`, `bombshell-day4.yaml`, `elimination-day5.yaml`. Each pins an `expected_hash`.

**Acceptance criteria.**
- `make qa` green.
- A 6-day playthrough can end three ways: player survives, player eliminated, recoupling drama (couples shuffle). All three covered by fixtures.
- `tests/engine/test_ceremonies.py` covers: deterministic NPC partner choice, bombshell insertion, elimination of unpartnered islander, public_perception bounds.

**Anti-goals.** No Casa Amor. No challenges system. No "Type on Paper" preference matching. No meta-progression (AP). No Producer agent. No real LLM.

---

## Phase D: Narrator Agent

**Design source:** [03-LLM-Architecture.md](../03-LLM-Architecture.md), [docs/decisions/0003-one-narrator-agent-for-v0.md](decisions/0003-one-narrator-agent-for-v0.md). Borrow patterns from `C:/Users/Mcian/projects/steno-livekit-agent/src/runtime/engine.py`.

**Scope.** Wire the single Narrator agent via `openai-agents`. Replace mock narration with real LLM narration in the default play path. Mock narration remains the default for tests.

**Changes.**
- [`agents/narrator.py`](../src/game/agents/narrator.py): build the `Agent[NarratorContext]` per steno's `build_engine_agent` pattern. Model: `claude-sonnet-4-6` hardcoded. One validated tool `commit_narration` whose Pydantic schema is `NarrationCommit { prose: str, tone: Literal[...] }`. `StopAtTools` on `commit_narration`. Prompt assembled from [`src/game/agents/prompts/narrator.md`](../src/game/agents/prompts/narrator.md) (existing) plus per-turn input.
- [`agents/narrator.py`](../src/game/agents/narrator.py): `narrate(result: MechanicalResult, visible_context: VisibleContext) -> Narration`. The Narrator gets archetype prose from `content/archetypes/<id>.md` (3 archetypes authored this phase), location mood from `content/locations/<id>.md` (4 locations), and the resolved `MechanicalResult`. Never the full state, never hidden values.
- Content authoring: `content/archetypes/{sweetheart,joker,friend}.md` and `content/locations/{pool,kitchen,terrace,bedroom}.md` with frontmatter (id, archetype/location label) and 80-150 words of prose flavor each. Loaded by [`src/game/content/loader.py`](../src/game/content/loader.py) into Pydantic models. `make content-lint` now validates these references.
- [`engine/turn.py`](../src/game/engine/turn.py): `run_turn` takes a `narrator: Narrator | None` parameter. If provided, use it; if not, use `mock_narration`. Default for tests: not provided. Default for CLI: provided. `--mock-llm` flag in `play` skips the real Narrator.
- [`cli/commands/play.py`](../src/game/cli/commands/play.py): construct the Narrator on startup unless `--mock-llm`. Pass to `run_turn`.
- Cost stance superseded by `docs/build-plan-F.md`: no per-call budget cap, no spend tracker, no `LLM_BUDGET_USD` env var. Game feel is the constraint.
- Tests: `tests/agents/test_narrator_quality.py`, marked `@pytest.mark.llm`. Five fixed `MechanicalResult` inputs. Hard structural checks per output: no digits in prose, no NPC names not in visible context, prose length 20-150 words, tone in allowed set. `make test-llm` runs them. Cost cap on the test run: 5 calls.

**Acceptance criteria.**
- `make qa` green (no LLM in default).
- `make test-llm` runs 5 narrator quality tests, all pass.
- `make play` produces real Sonnet narration. Run one 6-day session manually, verify prose feels in-character. Save the session as `fixtures/snapshots/phaseD-narrated-session.json` and trace as `fixtures/traces/phaseD-narrated-session.json`.
- Determinism preserved: `make determinism` still passes — narration variability does not affect mechanical hashes.

**Anti-goals.** No Producer, Director, or Curator agent. No streaming. No prompt caching (Sonnet's automatic caching is fine, don't reinvent). No multi-provider abstraction. No content beyond the three archetypes and four locations. No archetype-specific success math — archetypes only affect narration, not mechanics (R15).

---

## Phase E: Report Generator and Review Packet

**Design source:** This document. Pattern from steno's [tools/cli/play/html_render.py](C:/Users/Mcian/projects/steno-livekit-agent/tools/cli/play/html_render.py).

**Scope.** Build the static HTML report generator. Produce the review packet.

**Changes.**
- [`cli/commands/report.py`](../src/game/cli/commands/) (new): `python -m src.game.cli report session <trace-path> --out <html-path>` renders one session as a self-contained HTML page. `... report balance --seeds 1000 --out <html-path>` runs 1000-seed balance simulation with mock narration and renders aggregate stats. `... report packet --out review-packet/` orchestrates the full packet build.
- [`src/game/reporting/`](../src/game/) (new package): `html.py` with Jinja2 templates (add `jinja2>=3.1` to deps), `balance.py` with the 1000-seed simulator. No chart library — render bars and distributions with inline CSS/HTML.
- Templates embed all CSS inline. No external links. No images. Pure text and tables. Each turn rendered as a card per the spec in [`docs/build-plan-A2-E.md`](build-plan-A2-E.md) (i.e., this doc).
- The packet build runs three full 6-day sessions with real Sonnet narration, each with a different seed and a different player approach (loyal, chaotic, strategic — encoded as three policy scripts in `scripts/fixtures/policy-{loyal,chaotic,strategic}.yaml`).
- The balance run uses mock narration only. No LLM cost.
- Codex writes `review-packet/notes.md` after generating the packet: max 2 pages, format: `What I noticed / What felt good / What felt off / Open questions`. Concrete, no hedging.

**Acceptance criteria.**
- `make qa` green.
- `python -m src.game.cli report packet --out review-packet/` produces the packet structure below, all files non-empty, all HTML opens correctly in a browser, no broken links, no external network requests.
- LLM cost for packet generation: ≤ $10. Three 6-day sessions × ~40 turns × Sonnet ~= within budget.
- The `review-packet/` is the final deliverable. Codex commits it under git (it's small — HTML and JSON, no binaries).

**Anti-goals.** No interactive UI. No Vite. No Node. No charts library. No external CDN. No JS interactivity beyond expand/collapse if absolutely needed. No animation. No images. Pure HTML+CSS, self-contained.

---

## Review Packet Specification

The packet that Phase E produces, sitting in `review-packet/`:

```
review-packet/
  index.html                            landing page with links to everything below
  sessions/
    session-01-loyal.html               full session, ~30-40 turns rendered as cards
    session-02-chaotic.html             same shape, different seed and policy
    session-03-strategic.html
  balance/
    distribution.html                   1000-seed run aggregates
    action-coverage.html                action frequency by phase
  narration-quality/
    sample-20-turns.html                20 narrated turns isolated, side-by-side with their mechanical results
    flagged.md                          turns Codex thought felt off, with seed/turn/hash and a sentence each
  artifacts/
    session-01.json                     snapshot user can load: make play SNAPSHOT=...
    session-01-trace.json               every turn's trace
    session-02.json
    session-02-trace.json
    session-03.json
    session-03-trace.json
  notes.md                              Codex's "what I noticed" (max 2 pages)
  how-to-reproduce.md                   exact commands to regenerate any session
```

Each per-turn card on a session page shows:
- Turn N · Day D · Phase · Location
- Visible state summary (affection / chemistry / trust per visible islander)
- Action taken with target
- Roll vs chance, outcome (Success / Miss)
- Relationship deltas
- Narration prose
- State hash

The user opens `index.html` and reviews in 30-60 minutes.

---

## Anti-Goals (Global)

These hold across all phases. They override anything else.

- ❌ No interactive web UI (Vite, React) in this plan. That is Phase F, decided after the user reviews the packet.
- ❌ No Producer, Director, or Curator agents. Narrator only.
- ❌ No new stats beyond the 5 from [02-Core-Mechanics.md](../02-Core-Mechanics.md).
- ❌ No new ADRs unless a genuinely new architectural decision is required. Incremental code does not need ADRs.
- ❌ No content authoring beyond what each phase explicitly requires (3 archetypes through Phase C, then 3 archetypes plus 4 locations in Phase D; nothing more).
- ❌ No multi-LLM-provider abstraction. Sonnet only, hardcoded.
- ❌ No "for future flexibility" abstractions (ENGINEERING R6).
- ❌ No `--no-verify`, no bare `# type: ignore`, no `# noqa` (R5).
- ❌ No git operations beyond commits (R14). No pushes, no rebases, no branch creation.
- ❌ No backwards-compat for old fixtures. Bump `SCHEMA_VERSION` and regenerate (R12).
- ❌ No production-grade error handling beyond R2 fail-loud.
- ❌ No deferring tests to "later" — every phase ends with tests covering what was added (R10).
- ❌ No edits to prior ADRs. ADRs are append-only.
- ❌ No new MCP servers, no new tools, no new dependencies beyond what each phase explicitly authorizes.

---

## LLM Budget

| Phase | LLM use | Cost cap |
|---|---|---|
| A1 closeout, A2, A3, B, C | none | $0 |
| D | narrator wiring + 5 quality tests | $1 |
| E | 3 full sessions × 6 days × Sonnet | $10 |
| **Total** | | **$15** |

`agents/narrator.py` tracks per-process USD spend. If projected to exceed cap, raise and stop. Report to user before continuing.

---

## Done Definition

The whole effort is done when all of the following are true:

1. Every phase commit exists with `make qa` green.
2. `docs/build-log.md` has one entry per phase.
3. `review-packet/` exists, all files non-empty, opens cleanly in a browser.
4. Total LLM spend ≤ $15.
5. User confirms receipt of the packet path.

After that, the user decides whether to proceed to Phase F (Vite UI) or iterate on game feel based on what the packet showed.
