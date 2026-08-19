# Build Plan: Phase H11 — Review UX (Slides, Bookmarks, Checkpoints)

> Historical build plan. This file is kept for implementation context only.
> Current planning lives in [current-plan.md](current-plan.md).

The game produces rich state but the review surface is wrong shape. Current `session.html` is a wall of turn cards with raw JSON artifacts behind links. The user can't quickly find the interesting moments, can't pop out detail without leaving the page, and can't test variations without replaying a full session.

H11 fixes all three:

- **Slides** — review a playthrough as a deck of coherent scenes (one conversation, one ceremony, one movement burst), not a chronological wall of turns.
- **Bookmarks** — two sources, both feeding a top navigation. Engine auto-emits structural bookmarks (ceremonies, anomalies). Claude reads the trace and writes qualitative bookmarks into a notes file the dashboard ingests.
- **Checkpoints** — auto-save at major boundaries, named checkpoints on demand, resume + branch flow so short tests cost a fraction of a full playthrough.

Same constraints as the rest of the report stack: self-contained HTML, no external CDN, no framework. Vanilla JavaScript is now in scope — no React, no jQuery, just `addEventListener` and `<dialog>` elements.

**Design sources:** [00-Game-Start-And-Setup.md § Audience Meter](../00-Game-Start-And-Setup.md), [docs/qa-strategy.md](qa-strategy.md). No game-design canon for review UX — H11 is a tooling phase.

**Operating contract:** See [build-plan-H-index.md](build-plan-H-index.md). Four sub-phases, four commits. Final acceptance is reviewing one real-LLM playthrough in the new dashboard.

---

## Architectural Decisions

### Scenes, not turns

A scene is a coherent narrative unit derived from the trace. The scene compiler in `src/game/reporting/scenes.py` walks the trace records and groups them:

| Scene type | Trigger | Contents |
|---|---|---|
| `conversation` | `START_CONVERSATION` opens → conversation closes | All exchanges (player line + NPC line), the wheel rendered for each turn, mechanical outcomes, memories created, conversation summary |
| `ceremony` | Ceremony event fires (Pairing Ceremony, heart_throb, Flush of Hearts return, elimination, final vote) | Event narration, before/after state diff, ranked couples afterward |
| `movement_burst` | ≥ 2 NPC movements in same turn OR player MOVE action | Resort map snapshot before + after, which NPCs went where with reasons |
| `gather_event` | Gather fires (H9.5) | The gather location, the producer text or ceremony that triggered it, who was there |
| `background_window` | A run of turns with notable background dialogue but no player conversation | Background convo summaries from the run, memories that propagated as gossip |
| `day_boundary` | Phase wraps from EVENING to MORNING | Daily recap (H9.6), end-of-day audience ranking, couples standing |
| `character_creation` | Turn 0 with `CREATE_CHARACTER` action | Archetype card, stat allocation, starter advantage |

Scenes are sequential (every trace record belongs to exactly one scene). Each scene has a unique `scene_id`, a `turn_range`, and a `kind`. Approximately 15-30 scenes per 6-day run.

The HTML renders one scene at a time. Keyboard arrows + day timeline jump between scenes.

### Vanilla JS scope

Native browser primitives only:

- `addEventListener` for slide navigation (arrow keys, click)
- `<dialog>` element for popouts (native browser modal with `showModal()` / `close()`)
- `<details>` / `<summary>` for collapsible sections (already used by H6)
- CSS Grid for the three-panel layout (header / main / side)
- `position: sticky` for the side panel
- Plain DOM manipulation — no Virtual DOM, no framework, no build step

All JS lives as a single embedded `<script>` block in the generated HTML, alongside the inline CSS. The HTML file is fully self-contained — opens with no server, no network.

### Side state panel structure

Sticky on the right (desktop) or pulled into a drawer (mobile). Always-visible content:

- Player's archetype, persona (if autopilot), gender
- Current day / phase from the active scene
- Player's stats
- Player's current couple (with strength bar) + audience rank
- The 8 cast members as small avatar cards
- Each cast card is clickable → opens a popout

Clicking a cast avatar opens a popout `<dialog>` containing:

- Name, age, archetype, location at this scene's turn
- Backstory paragraph (H9.3)
- Revealed Type on Paper bits (H3)
- Relationship breakdown with player (affection, chemistry, trust, friendship — visual bars, no raw numbers required to be visible)
- Recent memories about the player (last 5, in their voice)
- Recent memories about other heartbreakers (last 5 — these are the gossip seeds the player could ask about)
- Current mood

The popout is keyboard-dismissable (`Escape` closes). Closing the popout returns focus to the main scene.

### Bookmark sources

**Auto-bookmarks** (engine-emitted, in trace):

The trace gains a `bookmarks: list[Bookmark]` field per turn. Engine emits these deterministically when:

| Bookmark kind | Trigger |
|---|---|
| `ceremony` | Any ceremony event fires |
| `flush_of_hearts_entry` | Player enters Flush of Hearts resort |
| `flush_of_hearts_return` | Day 6 morning return ceremony |
| `private_suite` | Paradise Suite used |
| `heart_throb_arrival` | New heartbreaker arrives |
| `elimination` | Any heartbreaker eliminated |
| `final_vote` | Final vote ceremony fires |
| `drama_memory` | A memory of weight ≥ 8 is created |
| `gather_event` | Gather event fires (H9.5) |
| `pull_failure` | A private-chat attempt fails |
| `interruption_ignored` | Player ignores an interruption (H9.5) |
| `npc_summoned` | NPC summoned out of player conversation (H8.2) |
| `gossip_propagated` | Memory propagated via told_by chain (H10.2) |
| `validation_retry` | Any agent retry-after-validation-failure |
| `outcome` | Run reaches final outcome (won, runner-up, eliminated, left single) |

Each `Bookmark` has: `turn`, `scene_id` (resolved by scene compiler), `kind`, `title` (auto-generated short), `category` (one of `event`, `highlight`, `anomaly`, `error`).

**Reviewer bookmarks** (Claude-authored, separate file):

A reviewer (me) reads a recorded trace and posts qualitative bookmarks to `review-notes.json` next to the trace:

```json
{
  "trace_path": ".game_traces/h11-loyal.json",
  "reviewer": "claude",
  "reviewed_at": "2026-05-15T14:30:00Z",
  "bookmarks": [
    {
      "turn": 12,
      "category": "anomaly",
      "title": "Wheel labels felt generic",
      "note": "Three of the four options were category-templates without specific moment reference. Could indicate the bespoke layer didn't fire."
    },
    {
      "turn": 28,
      "category": "highlight",
      "title": "Real gossip moment with Chloe about Marcus",
      "note": "She brought up what she saw at the pool unprompted. Naturally integrated."
    }
  ]
}
```

A new CLI subcommand `python -m src.game.cli review notes add --trace TRACE --turn N --category C --title "..." --note "..."` appends bookmarks. The dashboard ingests `review-notes.json` if present.

Reviewer bookmark categories:
- `highlight` — something worked well
- `anomaly` — something felt off but isn't broken
- `regression` — something got worse since a prior trace (compare against the named baseline)
- `smell` — code/architecture concern surfaced through play
- `note` — observation, no judgment

### Checkpoint system

Three checkpoint types:

1. **Auto-checkpoints** — engine writes a snapshot at every major boundary. Stored at `.game_saves/auto/<seed>/<day>_<phase>.json`. Boundaries: day rollover, post-ceremony, pre-Flush-of-Hearts, post-Flush-of-Hearts-return, pre-final-vote.

2. **Named checkpoints** — player creates via slash command in `make play`: `/checkpoint <name>`. Stored at `.game_saves/named/<name>.json`. Includes both the snapshot and the trace-so-far.

3. **Resume** — `make play --from-checkpoint <name|auto/path>` loads the checkpoint and continues from there. New trace records append to the original trace fork point (forked traces save to `.game_traces/<original>_<branch>.json`).

For branching: from one checkpoint, multiple resume sessions produce divergent traces. A new CLI subcommand `python -m src.game.cli report compare CHECKPOINT TRACE_A TRACE_B --out compare.html` renders a side-by-side diff showing where the branches diverged turn-by-turn (action chosen, NPC reaction, state delta).

This shifts testing from "run a 30-min full playthrough to test one variation" to "load checkpoint, run 5 minutes of variation A, run 5 minutes of variation B, diff in dashboard."

---

## Phase H11.1 — Slide-Based HTML Review

**Scope.** Replace the long-scroll `session.html` with a slide deck. Scene compiler groups trace records into coherent scenes. Three-panel layout: header (timeline + bookmarks placeholder), main (current scene), sticky side (state panel — empty in H11.1, populated in H11.2). Keyboard navigation. Vanilla JS embedded.

### Changes

**New module (`src/game/reporting/scenes.py`):**
- `Scene` Pydantic model with `scene_id`, `kind`, `turn_range`, `title`, `body` (raw rendering payload).
- `compile_scenes(trace_records) -> list[Scene]` walks the trace and groups records by kind.

**New module (`src/game/reporting/slides/__init__.py`):**
- `render_slide_deck(scenes, final_state, packet_meta) -> str` returns full HTML.
- `render_scene(scene) -> str` returns one scene's HTML body.
- `slide_navigation_js() -> str` returns the embedded vanilla JS for slide nav + popout.
- `slide_layout_css() -> str` returns the CSS for the three-panel layout.

**New module (`src/game/reporting/slides/scene_renderers.py`):**
- One function per scene kind: `render_conversation_scene`, `render_ceremony_scene`, `render_movement_burst_scene`, `render_gather_event_scene`, `render_background_window_scene`, `render_day_boundary_scene`, `render_character_creation_scene`.
- Each returns HTML for that scene's central panel.

**Existing file changes:**
- [`src/game/reporting/html.py`](../src/game/reporting/html.py): `session_page` becomes a thin wrapper that calls `compile_scenes` + `render_slide_deck`. Old long-scroll renderer becomes `session_page_legacy` and kept available behind the `--minimal` flag in `report.py`.
- [`src/game/cli/commands/report.py`](../src/game/cli/commands/report.py): `report packet` defaults to slide deck. `--minimal` falls back to the long-scroll version. `--legacy-html` (new alias) does the same.

### Tests

`tests/reporting/test_scene_compiler.py`:
- `test_compile_scenes_groups_conversation_records`
- `test_compile_scenes_emits_ceremony_scene_per_event`
- `test_compile_scenes_emits_movement_burst_only_for_multi_movements`
- `test_compile_scenes_emits_day_boundary_at_phase_wrap`
- `test_compile_scenes_assigns_unique_scene_ids`
- `test_compile_scenes_every_trace_record_belongs_to_one_scene`

`tests/reporting/test_slides.py`:
- `test_render_slide_deck_self_contained_no_external_refs`
- `test_render_slide_deck_includes_vanilla_js_for_nav`
- `test_render_conversation_scene_includes_all_exchanges`
- `test_render_ceremony_scene_includes_before_after_state`
- `test_render_day_boundary_scene_includes_recap`
- `test_legacy_renderer_still_works`

### Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] Generating the packet from a recorded trace produces a slide deck HTML by default.
- [ ] Arrow keys navigate prev/next scene.
- [ ] Each scene type renders distinctly (conversation looks different from ceremony, etc.).
- [ ] HTML is self-contained: no external CSS, JS, fonts, images, or CDN refs.
- [ ] HTML opens cleanly in Chrome, Firefox, Safari, Edge.
- [ ] `--minimal` flag still produces the long-scroll legacy renderer.

### Anti-goals

- No JS frameworks (React, Vue, jQuery, Svelte). Vanilla DOM only.
- No external CDN or fonts. System fonts as established.
- No PDF generation. HTML only.
- No animation libraries. Native CSS transitions for slide changes are fine.
- No build step. HTML is generated by Python and ready to open.

---

## Phase H11.2 — State Side Panel + Popouts

**Scope.** Side panel populated with persistent state across all scenes. Cast avatars are clickable, each opening a popout `<dialog>` with full NPC details. Same for couple status and player state.

### Changes

**New module (`src/game/reporting/slides/state_panel.py`):**
- `render_state_panel(final_state, current_scene_index, all_scenes) -> str` returns the side panel HTML. The panel shows state as-of the current scene's turn (so navigating updates the side panel via embedded JS).
- `render_cast_avatar(heartbreaker, scene_state) -> str` returns the small clickable avatar card.
- `render_npc_popout(heartbreaker, scene_state) -> str` returns the `<dialog>` body for an NPC popout.
- `render_couple_popout(couple, scene_state) -> str` returns couple-detail popout.

**Side panel structure:**
- Player block: avatar, name (or "You"), archetype, persona (if autopilot), gender, current stats as bars.
- Player's couple block: both avatars, couple strength bar, audience rank.
- Cast grid: 8 small avatars in a 4x2 grid (or 2x4 mobile). Click each → popout.
- Day indicator: current day, phase, time remaining (H8.1) from the active scene's snapshot.

**Popout contents (NPC):**
- Name, age, archetype, current location, current mood, current public perception.
- Backstory paragraph (H9.3).
- Revealed Type on Paper bits (H3) — shown as a small list. Unrevealed bits shown as `???`.
- Relationship with player: four bars (affection, chemistry, trust, friendship). No raw numbers — width of bar tells the story.
- Recent memories about the player (last 5, in their voice).
- Recent memories about other heartbreakers (last 5, with the subject's avatar inline).
- Their current mood with a one-line description.

**Popout contents (Couple):**
- Both partners' avatars, couple strength bar, audience rank.
- Day formed.
- Recent shared activity (last conversation, ceremony involvement).

**JS additions to `slide_navigation_js`:**
- `openPopout(id)` — calls `dialog.showModal()`.
- `closePopout(id)` — calls `dialog.close()`. Escape key default closes.
- `updateSidePanelState(sceneIndex)` — swaps in the right state for the current scene (data is baked into the HTML; JS picks the right snapshot per scene).

**State snapshots per scene:**
- The scene compiler now also produces a `scene_state_snapshot` per scene — the canonical state at the start of that scene. Used to render side panel correctly when navigating.
- Embedded in the HTML as inline JSON in a `<script type="application/json">` block (this is rendered text, not visible to the user — used only by the JS to swap state on navigation).

### Tests

`tests/reporting/test_state_panel.py`:
- `test_state_panel_includes_all_eight_cast_avatars`
- `test_state_panel_highlights_player_couple`
- `test_npc_popout_shows_backstory_and_revealed_bits`
- `test_npc_popout_hides_unrevealed_type_on_paper`
- `test_couple_popout_shows_strength_bar`
- `test_state_snapshot_per_scene_embedded`
- `test_no_raw_numerical_relationship_values_visible_by_default`

### Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] Side panel always visible on desktop, drawer-collapsible on mobile.
- [ ] Clicking any cast avatar opens a modal popout with NPC details.
- [ ] Pressing Escape closes the popout and returns focus to the main scene.
- [ ] Navigating between scenes updates the side panel state correctly.
- [ ] No raw JSON visible in popouts or panels.
- [ ] Unrevealed Type on Paper bits show as `???`.

### Anti-goals

- No exposing hash strings to users in the main UI (debug-only views can show them).
- No exposing raw delta JSON in popouts. Use bars and prose.
- No popouts inside popouts (one level of modal depth).

---

## Phase H11.3 — Bookmarks (Auto + Reviewer Notes)

**Scope.** Engine emits structural bookmarks per turn. New CLI `review notes add` lets a reviewer (Claude or human) append qualitative bookmarks to a `review-notes.json` file. Dashboard ingests both and renders a top navigation strip with categorized bookmarks.

### Changes

**State extension:**
- Trace records gain `bookmarks: list[Bookmark]` per turn.
- New `Bookmark` Pydantic model: `kind`, `category` (event/highlight/anomaly/error), `title`, `note` (optional). Hash-included.

**Engine bookmark emitters:**
- `src/game/engine/bookmarks.py` (new) — pure helpers `bookmark_for_ceremony`, `bookmark_for_pull_failure`, `bookmark_for_drama_memory`, etc. Returns `list[Bookmark]` for the current turn.
- `engine/turn.py` calls these after each turn is fully resolved. Appends to the trace record's bookmarks.

**Reviewer notes file format:**

`review-notes.json` next to the trace file. Schema validated on dashboard load:

```python
class ReviewerNote(BaseModel):
    turn: int
    category: Literal["highlight", "anomaly", "regression", "smell", "note"]
    title: str                  # short, displayed in nav
    note: str                   # longer, displayed in popout

class ReviewerNotesFile(BaseModel):
    trace_path: str
    reviewer: str               # "claude" or "human"
    reviewed_at: str            # ISO timestamp
    bookmarks: list[ReviewerNote]
```

**CLI additions:**
- `python -m src.game.cli review notes add --trace TRACE --turn N --category C --title "..." --note "..."` — appends a bookmark to `review-notes.json` for the given trace. Creates the file if missing.
- `python -m src.game.cli review notes list --trace TRACE` — prints existing bookmarks for the trace.
- `python -m src.game.cli review notes clear --trace TRACE` — clears all reviewer bookmarks (auto-bookmarks unaffected since they live in the trace).

**Dashboard ingestion:**
- `report packet --trace TRACE --out OUT` automatically picks up `review-notes.json` if it exists adjacent to the trace.
- The slide deck's header strip shows: a list of bookmarks ordered by turn, grouped by category (events on top, highlights green, anomalies orange, errors red, reviewer notes blue).
- Each bookmark is a clickable chip that jumps to the corresponding scene.
- The chip's title is the bookmark's `title`. Hovering shows the `note` if any.

**Scene-to-bookmark mapping:**
- The scene compiler resolves each bookmark's `turn` to its containing scene's `scene_id`.
- Click → jumps to scene via the same JS used for arrow nav.

### Tests

`tests/engine/test_bookmarks.py`:
- `test_bookmark_for_ceremony_emits_event_category`
- `test_bookmark_for_drama_memory_emits_highlight`
- `test_bookmark_for_pull_failure_emits_anomaly`
- `test_bookmark_for_validation_retry_emits_error`
- `test_engine_emits_bookmarks_per_turn`

`tests/cli/test_review_notes.py`:
- `test_review_notes_add_creates_file`
- `test_review_notes_add_appends_to_existing_file`
- `test_review_notes_list_prints_all_bookmarks`
- `test_review_notes_clear_removes_all_reviewer_entries`

`tests/reporting/test_bookmarks_render.py`:
- `test_dashboard_renders_auto_bookmarks_from_trace`
- `test_dashboard_renders_reviewer_notes_when_file_present`
- `test_dashboard_skips_reviewer_notes_when_file_absent`
- `test_bookmark_chips_link_to_correct_scene`
- `test_bookmark_categories_color_coded`

### Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] Trace records contain auto-bookmarks per the kind list.
- [ ] `review notes add` CLI works and creates `review-notes.json`.
- [ ] Dashboard top strip shows bookmarks grouped by category, color-coded, clickable.
- [ ] Clicking a bookmark jumps to its scene and highlights it briefly.
- [ ] Reviewer notes file is optional — packet builds fine without it.

### Anti-goals

- No LLM agent that auto-generates reviewer bookmarks. Bookmarks are either deterministic engine output or human/Claude-authored via the CLI.
- No editing auto-bookmarks via CLI (those live in the trace, immutable).
- No bookmark voting/threading. Each bookmark is independent.

---

## Phase H11.4 — Checkpoints

**Scope.** Auto-save snapshots at major boundaries. Slash command for named checkpoints. `play --from-checkpoint` resumes. New `report compare` subcommand diffs two branches from the same checkpoint.

### Changes

**State helpers (`src/game/state/snapshot.py`):**
- `save_named_checkpoint(state, name, trace_records) -> Path` — writes `.game_saves/named/<name>.json` containing snapshot + trace-so-far.
- `save_auto_checkpoint(state, seed, day, phase, trace_records) -> Path` — writes `.game_saves/auto/<seed>/<day>_<phase>.json`.
- `load_checkpoint(name_or_path) -> tuple[GameState, list[TurnTrace]]` — loads either a named checkpoint or an auto-path. Returns the state and the trace records leading up to it.

**Auto-checkpoint triggers (`engine/turn.py`):**
After turn execution, if any of these are true, write an auto-checkpoint:
- Day rolled over (phase wrapped EVENING → MORNING)
- Ceremony fired (Pairing Ceremony, heart_throb, elimination, final vote)
- Flush of Hearts entered or returned
- Paradise Suite used
- Final outcome assigned

**CLI play (`cli/commands/play.py`):**
- New slash command `/checkpoint <name>` saves a named checkpoint mid-play. Confirms with the path.
- New flag `--from-checkpoint <name|path>` to `make play`. Loads the checkpoint and continues. The trace records are pre-populated from the loaded checkpoint, and new records append.
- New flag `--branch-name <name>` for use with `--from-checkpoint`. Forks the trace to `.game_traces/<original>_<branch>.json` instead of writing to the original.

**Resume mechanics:**
- When `--from-checkpoint X` is set, the engine doesn't re-run character creation — the state already has it.
- The phase clock resumes at the checkpoint's saved value.
- Active conversations resume cleanly (state.active_conversation is preserved).
- Active NPCNPCConversations resume too.

**Branch comparison:**
- New CLI: `python -m src.game.cli report compare --checkpoint NAME_OR_PATH --trace-a PATH --trace-b PATH --out OUT.html`
- Loads both traces.
- Identifies the fork point (the checkpoint).
- Renders side-by-side scene-by-scene from the fork point: branch A's scene N vs branch B's scene N.
- Shows where they diverge (different actions chosen, different outcomes, different memories).
- Helpful summary at top: "Branches diverge at turn N when A chose X and B chose Y. By the end, A is in couple AB while B was eliminated."

### Tests

`tests/state/test_checkpoints.py`:
- `test_save_named_checkpoint_creates_file_at_expected_path`
- `test_load_checkpoint_restores_state_and_trace`
- `test_load_checkpoint_preserves_active_conversation`
- `test_load_checkpoint_preserves_npc_conversations`
- `test_load_checkpoint_preserves_phase_clock`

`tests/engine/test_auto_checkpoints.py`:
- `test_auto_checkpoint_on_day_rollover`
- `test_auto_checkpoint_after_ceremony`
- `test_auto_checkpoint_on_flush_of_hearts_entry`
- `test_auto_checkpoint_on_private_suite_use`

`tests/cli/test_checkpoint_flow.py`:
- `test_slash_checkpoint_creates_named_save`
- `test_from_checkpoint_resumes_play`
- `test_branch_name_forks_trace_file`

`tests/cli/test_report_compare.py`:
- `test_report_compare_identifies_fork_point`
- `test_report_compare_renders_side_by_side`
- `test_report_compare_summarizes_divergence_at_top`

### Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] Auto-checkpoints appear under `.game_saves/auto/<seed>/` after each boundary.
- [ ] `/checkpoint <name>` in `make play` saves a named checkpoint.
- [ ] `make play --from-checkpoint <name>` resumes from the checkpoint cleanly.
- [ ] Two branched playthroughs can be compared via `report compare`, producing a readable side-by-side HTML.
- [ ] Active conversations survive a checkpoint round-trip.

### Anti-goals

- No save scumming UX — the game design says no save scumming. Checkpoints are a *development testing tool*, not an in-game mechanic. Auto-checkpoints write to disk silently; manual checkpoints require an explicit slash command. No "load earlier" option mid-conversation.
- No checkpoint editing UI. Snapshots are immutable.
- No more than 3-way branch comparison (one-checkpoint, two-branch in v0).
- No checkpoint cleanup automation. User can delete `.game_saves/` as needed.

---

## Repo structure after H11

The relevant additions:

```
src/game/
├── engine/
│   └── bookmarks.py                    (H11.3)
├── reporting/
│   ├── scenes.py                        (H11.1)
│   ├── slides/
│   │   ├── __init__.py
│   │   ├── scene_renderers.py           (H11.1)
│   │   └── state_panel.py               (H11.2)
│   └── html.py                          (modified)
├── state/
│   └── snapshot.py                      (extended for checkpoints, H11.4)
└── cli/
    └── commands/
        ├── review.py                    (new, for `review notes add/list/clear`, H11.3)
        ├── report.py                    (extended for `report compare`, H11.4)
        └── play.py                      (extended for `/checkpoint`, `--from-checkpoint`, `--branch-name`, H11.4)

.game_saves/
├── auto/<seed>/<day>_<phase>.json       (H11.4 — gitignored)
└── named/<name>.json                    (H11.4 — gitignored)

tests/
├── reporting/
│   ├── test_scene_compiler.py           (H11.1)
│   ├── test_slides.py                   (H11.1)
│   ├── test_state_panel.py              (H11.2)
│   └── test_bookmarks_render.py         (H11.3)
├── engine/
│   ├── test_bookmarks.py                (H11.3)
│   └── test_auto_checkpoints.py         (H11.4)
├── state/
│   └── test_checkpoints.py              (H11.4)
└── cli/
    ├── test_review_notes.py             (H11.3)
    ├── test_checkpoint_flow.py          (H11.4)
    └── test_report_compare.py           (H11.4)
```

---

## Workflow after H11

The new review workflow becomes:

1. **Codex runs an autopilot session or user records a manual session.**
   ```bash
   make play --autopilot --persona loyal --seed 42 --record .game_traces/h11-loyal.json
   ```

2. **Codex generates the packet.** Slide deck dashboard at `review-packet/index.html`.
   ```bash
   python -m src.game.cli report packet --trace .game_traces/h11-loyal.json --out review-packet
   ```

3. **Claude reads the trace and adds reviewer bookmarks.**
   ```bash
   python -m src.game.cli review notes add --trace .game_traces/h11-loyal.json \
     --turn 28 --category highlight \
     --title "Real gossip moment with Chloe about Marcus" \
     --note "She brought up what she saw at the pool unprompted. Naturally integrated."
   ```
   Claude posts multiple bookmarks per trace, then re-generates the packet (which picks up the notes file automatically).

4. **User opens the dashboard.** Slide deck with top-bar bookmarks. Clicks any bookmark to jump to a scene. Side panel always shows state. Click NPC avatars for full details. No raw JSON.

5. **For testing variations: Codex uses checkpoints.**
   ```bash
   # Create a named checkpoint at an interesting moment
   make play  # play to day 3 evening, then type /checkpoint pre-Pairing Ceremony
   
   # Branch and try two variations
   make play --from-checkpoint pre-Pairing Ceremony --branch-name loyal-Pairing Ceremony --record .game_traces/...
   make play --from-checkpoint pre-Pairing Ceremony --branch-name chaotic-Pairing Ceremony --record .game_traces/...
   
   # Compare
   python -m src.game.cli report compare --checkpoint pre-Pairing Ceremony \
     --trace-a .game_traces/h11-loyal_loyal-Pairing Ceremony.json \
     --trace-b .game_traces/h11-loyal_chaotic-Pairing Ceremony.json \
     --out compare.html
   ```
   Two 5-min branches instead of two 30-min playthroughs. Claude reviews the comparison HTML.

---

## Done checklist for Codex

### H11.1 — Slide-Based HTML Review
- [ ] Write `engine/reporting/scenes.py` with scene compiler
- [ ] Write `engine/reporting/slides/scene_renderers.py` with one renderer per scene kind
- [ ] Write `engine/reporting/slides/__init__.py` with `render_slide_deck`, CSS, embedded JS
- [ ] Modify `engine/reporting/html.py` to default to slides
- [ ] Add `--minimal` / `--legacy-html` flag for the old long-scroll
- [ ] Tests: scene compiler, slide renderer, self-containment
- [ ] Run `make qa`, `make test-llm`
- [ ] Verify open in Chrome/Firefox/Safari/Edge with arrow key nav working
- [ ] Append build log
- [ ] Commit: `Phase H11.1: slide-based HTML review`

### H11.2 — State Side Panel + Popouts
- [ ] Write `engine/reporting/slides/state_panel.py` with side panel, NPC popout, couple popout
- [ ] Extend scene compiler to produce `scene_state_snapshot` per scene
- [ ] Embed scene snapshots as inline JSON for JS state-swapping
- [ ] Vanilla JS: `openPopout`, `closePopout`, `updateSidePanelState`
- [ ] Mobile drawer behavior for side panel under 700px width
- [ ] Tests: state panel rendering, popout content, no raw JSON visible
- [ ] Run `make qa`, `make test-llm`
- [ ] Verify popouts in browser: click avatar → modal opens with NPC details, Escape closes
- [ ] Append build log
- [ ] Commit: `Phase H11.2: state side panel and popouts`

### H11.3 — Bookmarks (Auto + Reviewer)
- [ ] Add `Bookmark` Pydantic model, extend trace records with `bookmarks: list[Bookmark]`
- [ ] Write `engine/bookmarks.py` with auto-bookmark emitters per kind
- [ ] Wire into `engine/turn.py` to emit after each turn
- [ ] Add `ReviewerNote`, `ReviewerNotesFile` Pydantic models
- [ ] Write `cli/commands/review.py` with `notes add`, `notes list`, `notes clear`
- [ ] Update `report packet` to ingest `review-notes.json` if present
- [ ] Render top-bar bookmark navigation in slide deck (categorized, color-coded, clickable)
- [ ] Bookmark chips link to scenes via JS
- [ ] Tests: auto-bookmarks, review notes CLI, dashboard rendering of both
- [ ] Run `make qa`, `make test-llm`
- [ ] Append build log
- [ ] Commit: `Phase H11.3: bookmarks (auto and reviewer)`

### H11.4 — Checkpoints
- [ ] Extend `state/snapshot.py` with `save_named_checkpoint`, `save_auto_checkpoint`, `load_checkpoint`
- [ ] Wire auto-checkpoint triggers into `engine/turn.py`
- [ ] Add `/checkpoint <name>` slash command to `cli/commands/play.py`
- [ ] Add `--from-checkpoint` and `--branch-name` flags to `play`
- [ ] Write `cli/commands/report.py` `report compare` subcommand
- [ ] Tests: snapshot round-trip with active conversations preserved, auto-checkpoint triggers, branch comparison rendering
- [ ] Run `make qa`, `make test-llm`
- [ ] Verify checkpoint flow manually: save → modify state via slash command → /checkpoint → resume → state matches
- [ ] Append build log
- [ ] Commit: `Phase H11.4: checkpoints and branch comparison`

### After all four commit

- [ ] Generate a packet from the most recent autopilot trace using the new slide deck
- [ ] Claude reviews the trace, posts 5-10 reviewer bookmarks, regenerates the packet
- [ ] User opens the dashboard, navigates with arrow keys, opens NPC popouts, jumps via bookmarks
- [ ] User confirms: no raw JSON visible, bookmarks make sense, popouts show real detail, side panel always-on works
- [ ] Test the checkpoint flow once: create a `/checkpoint pre-day-3`, branch into two short variations, compare via `report compare`

---

## Global anti-goals (H11-specific)

- ❌ No JS frameworks (React, Vue, jQuery, Svelte, Alpine, htmx). Vanilla DOM only.
- ❌ No external CDN, fonts, images, or any network resources in generated HTML.
- ❌ No build step. HTML is generated by Python.
- ❌ No PDF export. HTML only.
- ❌ No automated LLM-driven reviewer bookmarks. Engine auto-bookmarks are deterministic; reviewer bookmarks are Claude/human authored via CLI.
- ❌ No save-scumming UI. Checkpoints are dev tools; no in-game "load earlier" prompt.
- ❌ No edits to the prompts in this phase. H11 is reporting + state tooling, not agent work.
- ❌ No new agents.
- ❌ No reducing existing report content. The legacy renderer stays accessible via `--minimal`.

---

## What this phase produces

After H11 commits:

1. **Reviews are fast.** Open the dashboard, scan the bookmark strip, jump to the highlight or anomaly directly. No more scrolling through 100 turn cards looking for the interesting moment.
2. **Detail is one click away.** Click any NPC to see their backstory, current state, memories, mood. No raw JSON, no hunting through artifacts.
3. **Reviewer voice is in the dashboard.** Claude reads each trace, posts qualitative bookmarks, and the user sees them inline with the auto-bookmarks. The review process is a real artifact, not a separate document.
4. **Testing is fast.** Checkpoint + branch + compare lets Codex test variations in 5 minutes that would otherwise need a 30-minute playthrough each. Iteration tightens.
5. **The game stays the same.** H11 changes nothing about play, mechanics, dialogue, or agents. Only how the user reviews what happened.
