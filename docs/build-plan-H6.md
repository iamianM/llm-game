# Build Plan: Phase H6 — Stylish HTML Report

> Historical build plan. This file is kept for implementation context only.
> Current planning lives in [current-plan.md](current-plan.md).

The current `session.html` is utilitarian — a wall of turn cards in default fonts. H6 turns it into a reviewable artifact that's pleasant to read: typography, avatar placeholders, day-by-day timeline, couple status panel, public perception graph, memory web visualization. Same single-file, self-contained HTML constraint — no JS frameworks, no external CDN, no chart library. Pure HTML+CSS+SVG.

**Design sources:** [00-Game-Start-And-Setup.md § Audience Meter](../00-Game-Start-And-Setup.md), [10-Elimination-System.md § Audience System](../10-Elimination-System.md). No game-design canon for visual design — H6 is a UX phase.

**Operating contract:** See [build-plan-H-index.md](build-plan-H-index.md).

---

## Architectural Decisions

### Design language

Editorial / reality-TV style. Warm palette, serif body, sans-serif headers. Reads like a recap article. Concrete tokens:

| Token | Value |
|---|---|
| Body font | `Charter, Georgia, serif` |
| Header font | `Inter, -apple-system, BlinkMacSystemFont, sans-serif` |
| Background | `#f5f1eb` (warm cream) |
| Card background | `#ffffff` |
| Border | `1px solid #d8cfbd` |
| Accent (drama) | `#a4341a` |
| Accent (warmth) | `#5b7c4f` |
| Accent (cool) | `#3a5a73` |
| Success / win | `#1f6a3e` |
| Miss / cool | `#a4341a` |
| Body size | `17px` |
| Line height | `1.55` |

All CSS lives in `src/game/reporting/stylish/css.py` as a single string, embedded inline in the document. Self-contained.

### Layout

A session HTML page has three persistent regions and a scrollable timeline:

```
┌─────────────────────────────────────────────────┐
│  HEADER                                         │
│  ───────────────────────────────────────────────│
│  Recorded Playthrough — Heartthrob, Day 6      │
│  Final outcome: Won as couple with Chloe       │
│  Audience rank: 1 / 3 couples                  │
└─────────────────────────────────────────────────┘

┌────────────┬──────────────────┬─────────────────┐
│ DAY        │  TIMELINE        │  COUPLE STATUS  │
│ TIMELINE   │  (scrollable)    │  (sticky right) │
│ (sticky)   │                  │                 │
│            │  Day 1           │  You & Chloe    │
│ Day 1 ●    │  Morning · Pool  │  CS: 78        │
│ Day 2 ●    │  [conversation]  │  ──── chart    │
│ Day 3 ★    │                  │                 │
│ Day 4 ★    │  Day 1           │  Maya & Liam   │
│ Day 5 ★    │  Challenge ▲     │  CS: 62        │
│ Day 6 ★    │  Compatibility   │                 │
│            │  Quiz: SUCCESS   │                 │
│            │  ...             │                 │
└────────────┴──────────────────┴─────────────────┘

[Public Perception Graph]   [Memory Web]
─────────────────────────   ──────────────
```

### Avatar placeholders

Each NPC and the player get a small colored circle with their initials. Colors are deterministic from a hash of the heartbreaker id, so the same NPC has the same color across runs. Renders as inline SVG:

```html
<svg width="32" height="32" viewBox="0 0 32 32">
  <circle cx="16" cy="16" r="15" fill="#hash-derived-color"/>
  <text x="16" y="20" text-anchor="middle" font-size="12" fill="white">CH</text>
</svg>
```

No external assets. Helper function `avatar_svg(id, name) -> str` in `src/game/reporting/stylish/avatars.py`.

### Day timeline

Six day cells (or 8 if Flush of Hearts is in the trace) shown as a vertical navigation list on the left. Each day cell has a small icon indicating the highlight:

- ● Normal day
- ▲ Challenge day
- ◆ Pairing Ceremony day
- ★ Drama day (heart_throb / Flush of Hearts / elimination)

Click jumps to that day's section. Active day highlighted.

### Couple status panel

Sticky right column. Shows each active couple with:

- Both partners' avatars
- Couple strength as a horizontal bar
- Current public perception
- Trajectory arrow (up / flat / down vs. previous day)

Player's couple is visually emphasized (border highlight).

### Public perception graph

A simple line graph rendered as inline SVG. X axis = days 1-6. Y axis = 0-100. One line per couple, color-coded. No JS — just SVG polylines.

Function `perception_graph_svg(timeline_records) -> str` in `src/game/reporting/stylish/perception_graph.py`.

### Memory web

A node-edge graph showing who knows what. Each NPC is a node (their avatar circle). Each memory creates an edge from holder → subject, weighted by emotional_weight (line thickness). Different edge colors per source (direct = solid, witnessed = dashed, told_by = dotted).

Rendered as inline SVG with a simple force-directed layout computed at generation time (Python, deterministic). Function `memory_web_svg(memories, heartbreakers) -> str` in `src/game/reporting/memory_web.py`.

The web is shown once per run at the end of the report. Limited to memories above weight 4 to avoid clutter.

### Per-turn cards

Same structure as before but restyled:

- Subtle borders, generous padding.
- Speaker tags in small caps for dialogue.
- Body language italicized in muted color.
- Math breakdown in a collapsible details element, off by default. (Keeps the timeline scannable; you open math when you want detail.)
- Memories formed this turn rendered as small chips inline.

### Collapsibility

Days are collapsible (clicking the day title in the timeline collapses/expands its section). Default: current day expanded, prior days collapsed but expandable. Long playthroughs (40+ turns) stay scannable.

### Mobile

The three-column layout collapses to single column under 700px width. Sticky nav becomes a top bar.

---

## Changes by file

### New files

| File | Purpose |
|---|---|
| `src/game/reporting/stylish/__init__.py` | Package marker |
| `src/game/reporting/stylish/css.py` | The full CSS string |
| `src/game/reporting/stylish/avatars.py` | Avatar SVG generation |
| `src/game/reporting/stylish/timeline.py` | Day timeline + per-day section rendering |
| `src/game/reporting/stylish/couple_status.py` | Couple status sticky panel |
| `src/game/reporting/stylish/perception_graph.py` | SVG public perception graph |
| `src/game/reporting/memory_web.py` | SVG memory web visualization |
| `tests/reporting/test_stylish.py` | Unit tests for stylish renderers |

### Files changed

- [`src/game/reporting/html.py`](../src/game/reporting/html.py): Default `session_page` now uses the stylish renderer. Old utilitarian renderer becomes `session_page_minimal` (kept for tests).
- [`src/game/cli/commands/report.py`](../src/game/cli/commands/report.py): `report packet` renders the stylish version by default. Flag `--minimal` falls back to the old renderer if needed.
- [`src/game/reporting/html_blocks.py`](../src/game/reporting/html_blocks.py): Continues to exist as the source of per-turn card blocks; stylish renderer composes them within the new layout shell.

---

## Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] Generating a packet from any recorded trace produces a stylish session HTML by default.
- [ ] The session HTML is self-contained: no external CSS, no external JS, no external images, no CDN references.
- [ ] The HTML opens in Chrome, Firefox, Safari, and Edge with consistent layout.
- [ ] Header shows player archetype, current day, final outcome (if run is complete), and audience rank.
- [ ] Sticky day timeline on the left navigates to each day section.
- [ ] Sticky couple status panel on the right shows every active couple with strength bar.
- [ ] Public perception line graph renders one line per couple, color-coded.
- [ ] Memory web renders nodes for each non-eliminated heartbreaker, edges for memories of weight ≥ 4.
- [ ] Each per-turn card has avatars for the player and the NPC they spoke with.
- [ ] Math breakdown is collapsed by default and expandable.
- [ ] Mobile: under 700px width, layout collapses to single column.
- [ ] Flush of Hearts (if present in the trace) is visually marked in the timeline.
- [ ] A specific Paradise Suite turn (if present) is rendered with a distinct, gentler card style.
- [ ] Final outcome (if present) is rendered with a clear, dramatic end-of-report block.

---

## Tests

### Engine / reporting tests (non-LLM)

- `tests/reporting/test_stylish.py`:
  - `test_stylish_session_html_renders_with_minimal_trace`
  - `test_stylish_session_html_self_contained_no_external_refs`
  - `test_avatar_svg_color_deterministic_from_id`
  - `test_timeline_marks_challenge_day`
  - `test_timeline_marks_Pairing Ceremony_day`
  - `test_timeline_marks_flush_of_hearts_day`
  - `test_couple_status_panel_shows_all_active_couples`
  - `test_couple_status_panel_highlights_player_couple`
  - `test_perception_graph_renders_one_line_per_couple`
  - `test_memory_web_excludes_low_weight_memories`
  - `test_memory_web_renders_edge_styles_by_source`
  - `test_final_outcome_block_rendered_when_state_outcome_set`
  - `test_math_breakdown_collapsed_by_default`

### Visual tests

H6 doesn't add new gameplay scenarios — it consumes existing traces. Tests assert structural HTML properties (presence of specific class names, valid SVG, no external references) rather than visual fidelity. Visual fidelity is the user's review job.

---

## Evals (no new playthrough assertions)

H6 doesn't change gameplay logic, only rendering. No new assertions. Existing assertions all still pass.

But: the eval dashboard itself (`playthrough-eval.html`) gets the same stylish treatment in this phase. Function `render_eval_dashboard` in `src/game/reporting/eval_dashboard.py` uses the new stylish layout.

---

## Anti-goals

- ❌ No JS frameworks. No React, Vue, no jQuery. Native HTML5 only.
- ❌ No external CDN. No external fonts (system fonts only). No external images.
- ❌ No charting library. SVG is hand-built.
- ❌ No CSS frameworks. Tailwind / Bootstrap are out.
- ❌ No PDF generation. HTML only.
- ❌ No new gameplay mechanics — H6 is rendering-only.
- ❌ No prompt edits (R17).

---

## Done checklist for Codex

- [ ] Read [build-plan-H-index.md](build-plan-H-index.md) pre-flight
- [ ] Create `src/game/reporting/stylish/` package
- [ ] Write `css.py` with the full design-token CSS string
- [ ] Write `avatars.py` with deterministic SVG avatar function
- [ ] Write `timeline.py` for day navigation + per-day sections
- [ ] Write `couple_status.py` for the sticky panel
- [ ] Write `perception_graph.py` for SVG line graph
- [ ] Write `memory_web.py` for SVG memory graph
- [ ] Wire stylish renderer into `reporting/html.py` and `cli/commands/report.py`
- [ ] Keep the minimal renderer accessible via `--minimal` flag
- [ ] Apply the stylish layout to `eval_dashboard.py`
- [ ] Write `test_stylish.py` with structural assertions
- [ ] Regenerate the packet from an existing trace to verify visual rendering manually
- [ ] Run `make qa`; fix root causes
- [ ] Append to `docs/build-log.md`
- [ ] Commit: `Phase H6: stylish HTML report`
