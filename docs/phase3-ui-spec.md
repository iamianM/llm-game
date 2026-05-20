# Phase 3 — Paradise Hearts Player UI (MVP)

This is the spec for the first playable interface. The deterministic Python
engine is the asset; this phase wraps it in a Next.js visual-novel UI so the
game becomes something a person can *play* instead of inspect via the review
packet.

**Read also:**
- `paradise-hearts-glossary.md` — every player-facing string uses these terms
- `phase3-ui-design-system.md` — colors, fonts, motion, components
- `phase3-fastapi-contract.md` — REST + SSE between Next.js and Python
- `phase3-acceptance-and-testing.md` — what "done" means; Playwright + screenshots

## 0. North star

By the end of Phase 3, the following must be true:

A person can open a browser, click "New Run", pick an archetype, and play a
complete 6-day game of Paradise Hearts to its finale at Sunset Bay, with
real-LLM dialogue, Pulse signaling, and all current engine features (Day-1
intros, ambient, ceremonies, Flush of Hearts, Heart Swap proposals) visible
and working. No real art is required; placeholder art is the explicit MVP
scope.

All player-facing copy uses the Paradise Hearts vocabulary from
`paradise-hearts-glossary.md`. The cast are **Heartbreakers**, the location
is **Sunset Bay**, new arrivals are **Heart Throbs**, the rival twist is
the **Flush of Hearts**, re-pairings are **Heart Swaps**, audience score is
**Pulse**, eliminations are **Heart Out**, etc. Stress-test reference
paragraph at the bottom of the glossary doc — UI strings should match that
tone.

If a reasonable observer can't tell the difference between "the engine ran via
CLI and was rendered in the review packet" and "the engine ran via the UI and
the player saw it live", we've succeeded.

## 1. Architecture

Two services. Both run locally during development; both ship to one host
(e.g. Vercel + a Python backend on Fly.io or Railway) later.

```
[Browser]
  Next.js 14 app
    Tailwind CSS
    Zustand    (client state: UI flags, animation, current dialogue progress)
    TanStack Query  (server state: game state, polled / SSE-streamed)
    Headless UI (dialogs, listboxes)
    Lucide React (icons)
        │
        │   HTTP (JSON)  + SSE (typewriter streaming)
        ▼
[localhost:8000]
  FastAPI server (Python 3.11+)
    Thin REST adapter — no game logic of its own
    Calls into existing src/game/ modules
        │
        ▼
  Existing Python engine
    Deterministic turn loop
    Six LLM agents (Islander Voice, Contextual Options, Event Narrator,
                    Villa Orchestrator, Background Dialogue, Conversation Curator)
    State + memory + couples + audience
        │
        ▼
  OpenAI / Anthropic API
```

Key decisions:

1. **Engine stays Python.** Months of validated work; do not port to TypeScript.
2. **FastAPI is a thin adapter.** Target ~200 lines. No game logic; just
   translate HTTP requests into engine calls and engine state into JSON.
3. **SSE for dialogue streaming.** LLM-generated NPC lines stream from
   OpenAI → FastAPI → Next.js character-by-character. The "typewriter"
   effect is the actual model generating, not a fake delay. This makes the
   game feel alive.
4. **Auto-generated TypeScript types.** FastAPI's OpenAPI schema is consumed
   by `openapi-typescript` so the frontend gets free TS types for the engine
   state. Reduces drift.
5. **Single in-progress run, lost on refresh.** Persistence (localStorage or
   server-side) is Phase 4 territory. MVP is one in-memory run.

## 2. Repository layout additions

```
src/game/                  # existing — no changes
src/api/                   # NEW — FastAPI server
  __init__.py
  app.py                   # FastAPI application + routes
  models.py                # Pydantic request/response models
  session.py               # in-memory session storage (single user, single run)
  streaming.py             # SSE helpers for typewriter dialogue

web/                       # NEW — Next.js app
  app/
    layout.tsx
    page.tsx               # title screen
    new-run/
      page.tsx             # character creation flow
    play/
      [sessionId]/
        page.tsx           # main game stage
        ceremony/
          page.tsx         # ceremony overlay route
        finale/
          page.tsx         # finale screen
  components/
    stage/
      GameStage.tsx        # main visual-novel layout
      DialogueBox.tsx
      ChoiceMenu.tsx
      NpcPortrait.tsx
      VillaBackground.tsx
      TopBar.tsx
      AudienceMeter.tsx
      DayBadge.tsx
      ClockPill.tsx
    rail/
      RightRail.tsx
      VillaMap.tsx
      CastGrid.tsx
      CouplesPanel.tsx
      MemoriesList.tsx
    ceremony/
      CeremonyOverlay.tsx
      PairingList.tsx
      Narration.tsx
    chrome/
      TitleScreen.tsx
      ArchetypeCard.tsx
      DayRecap.tsx
      FinaleScreen.tsx
      SettingsMenu.tsx
    ui/
      Avatar.tsx           # initials in colored circle
      Button.tsx
      Pill.tsx
      Dialog.tsx
  lib/
    api.ts                 # typed API client
    store.ts               # Zustand store
    types.ts               # generated from FastAPI OpenAPI
    hooks/
      useTurn.ts
      useStreamedDialogue.ts
  styles/
    globals.css
    tokens.css             # CSS custom properties from design system
  public/
    backgrounds/           # CSS gradients in code; this dir is for future art
    avatars/               # ditto
  package.json
  tsconfig.json
  tailwind.config.ts
  postcss.config.js
  next.config.js

tests/
  api/                     # NEW — pytest tests for FastAPI
    test_session.py
    test_turn.py
    test_streaming.py

web/tests/                 # NEW — Playwright tests
  e2e/
    title.spec.ts
    new-run.spec.ts
    full-playthrough.spec.ts
    ceremony.spec.ts
    finale.spec.ts
  smoke/
    snapshot-pages.spec.ts # screenshots of every page state
```

## 3. Screens

### 3.1 Title screen (`/`)

**Layout:** centered column, dark cinematic background gradient.

- **Wordmark:** "Paradise Hearts" in Charter serif, ~64px, accent-orange
  color, gentle text-shadow for warmth
- **Tagline** below: "Make a Connection. Survive the Drama." — Inter, muted
- **Buttons** stacked: "New Run" (primary, accent), "Continue Run" (disabled,
  tooltip "coming soon"), "The Reunion" (disabled, tooltip "coming soon")
- **Footer**: version, build info, link to docs

**Interactions:** click New Run → navigate to `/new-run`.

### 3.2 Character creation (`/new-run`)

**Layout:** multi-step wizard. MVP = step 1 only; steps 2–4 stubbed with
defaults for now.

**Step 1: Archetype.** Three cards side by side:

- **Heartthrob** — +3 Charm, "Starter Chemistry" advantage
- **Class Clown** — +3 Banter, "Crowd Pleaser" advantage
- **Loyal Friend** — +3 Loyalty, "Strong Bonds" advantage

Each card: avatar circle (colored), name in Charter, stat bonus chip, one-line
flavor text, "Pick" button.

**Steps 2–4 (stubbed):** stat allocation (defaults to balanced 6/6/6/6/6),
Type on Paper (defaults to neutral), character card preview (read-only summary).

**On submit:** POST `/api/session/new` → receive `sessionId` → navigate to
`/play/{sessionId}`.

### 3.3 Main game stage (`/play/[sessionId]`)

The visual-novel layout. This is the screen the player spends 95% of their
time in.

**Layout (1280×800 desktop target):**

```
┌───────────────────────────────────────────────────────────────┐
│ ▼ Paradise Hearts  Day 1 · Afternoon · T8 · 14:35  ●●●○○  ⚙  │  56px top bar
├───────────────────────────────────────────────────────────────┤
│                                                          ┌──┐ │
│                                                          │ ▼│ │  rail toggle
│                                                          └──┘ │
│            (villa pool gradient background)                   │
│                                                               │
│                                                               │
│                   ⬤  Chloe portrait                           │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│   ┌─ Chloe ───────────────────────────────────────────────┐  │
│   │ *smiles softly* That actually feels good coming         │  │ dialogue box
│   │ from you.                                               │  │ ~30% of height
│   │                                                  ⟶     │  │
│   └────────────────────────────────────────────────────────┘  │
│   ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐          │
│   │ +  Ask  │ │   Joke  │ │ +  Flirt │ │ −  End   │          │  choice menu
│   │  deeper │ │  about… │ │  back    │ │  on good │          │
│   │ low·EQ  │ │ low·Ban │ │ med·Cha  │ │  note    │          │
│   └─────────┘ └─────────┘ └──────────┘ └──────────┘          │
└───────────────────────────────────────────────────────────────┘
```

**Top bar (56px):**
- Hamburger menu (left) — opens main menu (resume/settings/quit)
- Game title (Charter, small)
- Status chips: Day badge, Phase badge, Turn pill (T#), Clock pill (HH:MM)
- Audience meter: 5-dot gauge tinted gold/sage/bad based on perception
- Settings cog (right)

**Stage area:**
- Background gradient per location (pool = blue, kitchen = warm yellow, etc.;
  see design system)
- NPC portrait centered (placeholder colored circle, 200–240px diameter, soft
  shadow)
- Mood color flash on portrait when NPC's tone shifts (200ms tint overlay)
- If multiple NPCs present (gather/ceremony), 2–4 portraits arranged
  symmetrically

**Dialogue box:**
- Cream card, fixed at bottom 30% of viewport
- Name tag (Charter, accent color)
- Body text (Inter, 17–18px, comfortable line-height)
- Typewriter effect streamed via SSE
- "⟶" arrow indicator when ready for next action (typewriter complete)
- Click anywhere on box → fast-forward typewriter to complete

**Choice menu:**
- Render every action returned by the API. The browser must not silently cap,
  truncate, or reorder available actions; if the engine offers six valid
  choices, all six must be reachable.
- Buttons wrap on narrow viewports and the menu may scroll internally when the
  valid action set is larger than the available vertical space.
- Each button:
  - Pulse hint chip (+/-/empty) above the label
  - Label text
  - Risk + stat used (small muted text below)
  - Hover: subtle lift + glow
  - Click: locks selected button (others fade), sends turn
- Special button styling for exit options ("End conversation" etc.): dashed
  border, slightly muted

**Right rail (collapsible, 320px wide):**
- Toggle handle on right edge of stage
- Sections (each a small card):
  - **Where everyone is** (Sunset Bay map, same content as review packet)
  - **Couples** (current pairings, player highlighted)
  - **Heartbreakers** (8 portraits, click for popout)
  - **Memories** (player's recent memories)
- Default state: collapsed (handle visible)

**Cast popout dialog:**
- Same content as review packet's NPC popouts: backstory, relationship bars
  (affection/chemistry/trust/friendship), Type on Paper with familiarity gate,
  recent memories about you
- Opens in a modal overlay, dim background, close with ✕ or click-outside

### 3.4 Ceremony overlay (route: `/play/[sessionId]/ceremony`)

Special "feature" rendering for Pairing Ceremonies, Heart Throb arrivals,
Flush of Hearts announcements, and the finale.

**Layout:**
- Full-screen overlay; main stage dimmed to ~30% opacity behind it
- Background fades to deep `--bg` (warm near-black)
- Centered Charter serif narration prose, max-width 60ch, slow fade-in
- For pairing ceremonies and other events that actually form or reveal couples:
  animate the couples list in, one couple per row, 600ms stagger, avatars +
  names with "&" between
- Challenge, producer text, gather, and other non-pairing events must not show
  stale couples just because current couples exist in state.
- For Heart Throb arrivals: bigger portrait of the new arrival, name, intro
  line from the narrator
- "Continue" button at bottom - accent CTA, advances back to stage. It must
  remain visible and clickable even when the cast size grows to Flush of Hearts
  scale; long narration or pairing lists scroll inside the overlay.

### 3.5 Day boundary (modal overlay on stage)

End-of-day recap:
- Smaller cream card overlay (not full screen)
- Header: "Day 3 wraps"
- Recap bullets from `daily_recaps` (the engine already produces these)
- Pulse Board (couple, rank, score with arrow indicators)
- "Continue to Day 4" CTA

### 3.6 Finale screen (`/play/[sessionId]/finale`)

Cinematic outcome:
- Full-screen, gold accent palette
- "🏆 Finale" header (Charter, large)
- Winning couple front and center, avatars + names, final Pulse score
- Runner-up couple below
- Memorable moments callout (3–5 highlights from the run's high-weight memories)
- Stats: days survived, conversations had, Pulse peak/final
- Heart Beats earned (display "0 Heart Beats" with note "spend Heart Beats in The Reunion —
  coming Phase 4")
- "New Run" button + "Main Menu" link

## 4. Per-turn flow

What happens between the player clicking a choice and seeing the next state:

```
1. Player clicks a choice button
2. UI optimistically locks selection (fade other options, highlight chosen)
3. POST /turn { sessionId, kind, target_id, intent_id, option_index }
4. Server runs engine.run_turn(state, action)
5. Server begins streaming response via SSE:
     event: state
       full updated game state (JSON)
     event: dialogue.start
       { speaker, mood_before }
     event: dialogue.chunk
       { text: "*smiles* That actu" }   ← LLM streamed
     event: dialogue.chunk
       { text: "ally feels..." }
     event: dialogue.end
       { mood_after, audience_delta, deltas: {affection: +2} }
     event: options
       { menu: [...] }
     event: villa_update
       { interruptions, conversation_starts, ... }
     event: turn_end
       { state_hash }
6. UI consumes events:
   - state → updates store, animates Pulse meter / location / portraits
   - dialogue.start → swap to new speaker, typewriter cursor visible
   - dialogue.chunk → append to dialogue box, typewriter character-by-character
   - dialogue.end → enable "next" indicator, animate delta chips floating up
   - options → render new choice buttons
7. Wait for next click
```

Failure modes:
- Network drop mid-stream → resume request with `Last-Event-ID` header
- Backend error (5xx) → show toast, retry button, preserve player input
- Validation error (action not valid for state) → show inline error, restore
  choice menu

## 5. State management (frontend)

**Zustand store** for client-only state:
- `currentDialogue: string` — building up character-by-character
- `dialogueComplete: boolean`
- `typewriterSpeed: 'slow' | 'normal' | 'fast' | 'instant'` (settings)
- `autoAdvance: boolean` (settings)
- `rightRailOpen: boolean`
- `activeDialog: string | null` (cast popout, settings, etc.)

**TanStack Query** for server state:
- `useSession(sessionId)` → current game state
- `useTurn()` mutation → submit action, stream response
- `useCastDetail(npcId)` → on-demand popout content

Engine state never lives in Zustand — it's always the latest from the server.
This prevents drift.

## 6. Component inventory

### Stage components

- **`<GameStage>`** — root layout, takes session state, orchestrates children
- **`<TopBar>`** — title, status chips, Pulse meter, settings
- **`<VillaBackground>`** — CSS gradient based on `state.location_id`
- **`<NpcPortrait>`** — colored-circle avatar, name, optional mood tint flash
- **`<DialogueBox>`** — name tag + streaming text + next indicator
- **`<ChoiceMenu>`** — list of `<ChoiceButton>` with audience hints
- **`<ChoiceButton>`** — single option with hint chip, label, stat info
- **`<DeltaChip>`** — float-up animation for `+2 affection` type feedback
- **`<AudienceMeter>`** — 5-dot gauge with color
- **`<DayBadge>`**, **`<PhaseBadge>`**, **`<ClockPill>`**, **`<TurnPill>`**

### Rail components

- **`<RightRail>`** — collapsible container
- **`<VillaMap>`** — 4-cell grid, you-marker (same as review packet)
- **`<CouplesPanel>`** — list of couples with avatars
- **`<CastGrid>`** — 8 avatar tiles, opens popouts
- **`<CastPopout>`** — full NPC detail dialog (modal)
- **`<MemoriesList>`** — recent player memories, scrollable

### Ceremony / chrome

- **`<CeremonyOverlay>`** — full-screen feature scene
- **`<Narration>`** — typewritten serif prose, centered
- **`<PairingList>`** — animated couple-by-couple reveal
- **`<DayRecap>`** — modal end-of-day card
- **`<FinaleScreen>`** — cinematic outcome screen

### Title / creation

- **`<TitleScreen>`** — wordmark, tagline, buttons
- **`<ArchetypeCard>`** — selectable card for character creation
- **`<SettingsMenu>`** — typewriter speed, auto-advance, audio toggle (stub)

### UI primitives

- **`<Avatar>`** — colored circle with initials, configurable size
- **`<Button>`** — primary / secondary / disabled variants
- **`<Pill>`** — small label chip, configurable color
- **`<Dialog>`** — wraps Headless UI dialog with our styling
- **`<Hint>`** — small +/− chip for audience signaling

## 7. Browser support

- **Target:** Chrome / Edge / Safari latest, desktop only for MVP
- **Viewport:** 1280×800 minimum; design for 1440×900
- **Mobile / tablet:** explicit non-goal for MVP; will degrade poorly, that's OK
- **Accessibility:** keyboard navigation must work (Tab, Enter, Esc); screen
  reader labels on every interactive element; focus visible. WCAG AA color
  contrast.

## 8. Settings

A small persisted settings object (localStorage):
- **Typewriter speed:** Slow / Normal / Fast / Instant
- **Auto-advance after typewriter completes:** off / 1s / 2s / 3s
- **Audio:** N/A in MVP (UI present but disabled)
- **Skip seen dialogue:** N/A in MVP (no save-resume yet)
- **Reduce motion:** when on, disable transitions and float-up animations

## 9. Save / resume

**MVP scope:** localStorage persistence of `sessionId` and a periodic
checkpoint dump. On page load, if `sessionId` exists and the server still
holds the session, resume; otherwise restart at title.

Out of MVP: server-side persistence, multi-run history.

## 10. Out of scope (Phase 4+)

- Mobile responsive layout
- Real NPC portraits (commissioned or AI-generated)
- Real villa background art
- Audio (BGM, SFX, voice)
- The Reunion / meta-progression screen
- Run history and replay
- Multiple concurrent sessions
- Authentication / accounts
- Animated NPC expressions (happy/sad/angry/flirty sprite variants)
- Touchscreen / mobile interactions
- Offline mode

## 11. Step-by-step implementation plan for codex

This is the order codex should build in. Each numbered step is a checkpoint;
the project should be functional at the end of each (just less complete).

### Step 1: FastAPI scaffold

- Create `src/api/app.py` with FastAPI app, CORS for `localhost:3000`
- Pydantic models for: `NewSessionRequest`, `SessionState`, `TurnRequest`,
  `TurnResponse` (mirror the engine's data classes)
- Endpoints:
  - `POST /session/new` — create session, run character creation, return state
  - `GET /session/{id}` — current state snapshot
  - `POST /session/{id}/turn` — submit an action, return new state
  - `GET /session/{id}/cast/{npc_id}` — popout detail
  - `GET /session/{id}/stream` — SSE endpoint for streaming dialogue
- In-memory `SESSIONS: dict[str, GameSession]` keyed by UUID
- Tests: `tests/api/test_session.py`, basic happy-path
- Smoke: `uv run uvicorn src.api.app:app --reload --port 8000`, curl
  `POST /session/new`, verify response shape

**Done when:** can create a session and submit a turn via curl, receive JSON
back that matches the Pydantic schema.

### Step 2: Auto-generated TypeScript types

- Add `web/scripts/gen-types.ts` that hits `/openapi.json` and runs
  `openapi-typescript`
- Wire as `npm run gen:types`
- Output: `web/lib/types.ts`

**Done when:** running `npm run gen:types` produces a `types.ts` matching the
FastAPI schema; TS imports work in any component.

### Step 3: Next.js scaffold + design tokens

- `npx create-next-app@latest web --typescript --tailwind --app`
- Add design tokens (see `phase3-ui-design-system.md`) as CSS variables in
  `web/styles/tokens.css`
- Install: `zustand`, `@tanstack/react-query`, `@headlessui/react`,
  `lucide-react`, `react-type-animation`
- Set up Tailwind config with custom colors mapped to CSS variables
- Set up Charter, Inter, Caveat font loading via `next/font`
- Build the title screen (`app/page.tsx`) — wordmark, buttons, navigation

**Done when:** `npm run dev`, visit `localhost:3000`, see Paradise Hearts
title screen with proper fonts and colors. Click "New Run" → routes to
`/new-run` (placeholder page).

### Step 4: Character creation flow

- Build `<ArchetypeCard>` and the wizard at `/new-run`
- Wire to `POST /session/new` via TanStack Query
- On submit, navigate to `/play/[sessionId]`

**Done when:** pick an archetype, see a session created in FastAPI logs, land
on `/play/{uuid}` (placeholder page).

### Step 5: Stage skeleton

- `/play/[sessionId]/page.tsx` fetches session state on mount
- Build `<TopBar>`, `<VillaBackground>`, `<NpcPortrait>`, `<DialogueBox>`,
  `<ChoiceMenu>`, `<ChoiceButton>`
- Wire choice clicks to `POST /session/{id}/turn`
- For now, render dialogue all-at-once (no streaming yet — placeholder)

**Done when:** can play through a complete turn — see NPC line, click an
option, see the next NPC line. Engine state visibly updates (day, phase,
Pulse meter changes).

### Step 6: SSE streaming for typewriter

- Backend: `GET /session/{id}/stream` reads from the LLM stream and forwards
  chunks as SSE events
- Frontend: `useStreamedDialogue` hook subscribes via EventSource, appends
  chunks to `<DialogueBox>`
- "Click to fast-forward" support — complete the typewriter immediately

**Done when:** NPC dialogue visibly streams in character-by-character at
human-readable pace. Clicking on the dialogue box jumps to complete.

### Step 7: Right rail + popouts

- Build `<RightRail>` toggle
- Port `<VillaMap>`, `<CouplesPanel>`, `<CastGrid>` from review packet logic
- Build `<CastPopout>` dialog with full NPC detail
- Wire to `GET /session/{id}/cast/{npc_id}` for on-demand fetch

**Done when:** can toggle the rail open/closed, click a cast tile, see the
NPC popout with backstory + relationship bars + Type on Paper + memories.

### Step 8: Ceremony overlay

- Build `<CeremonyOverlay>`, `<Narration>`, `<PairingList>`
- When the engine emits a `ceremony_events` entry on a turn, the UI shifts
  to ceremony mode instead of the normal stage
- Animate couples in
- "Continue" returns to stage

**Done when:** Day-1 First Spark renders as a ceremony, then a Heart Throb
arrival later renders, then a Day-3 Pairing Ceremony renders, all distinct
from regular turns.

### Step 9: Day boundary + finale

- `<DayRecap>` modal at day boundary
- `<FinaleScreen>` at game end
- Route to `/play/{sessionId}/finale` when state.outcome is set

**Done when:** completing a full 6-day game lands on the finale screen with
winning couple + stats.

### Step 10: Audience signaling + deltas

- `<AudienceMeter>` in top bar reflects `player.public_perception`
- Audience hint chips render on `<ChoiceButton>` from
  `option.audience_hint`
- `<DeltaChip>` floats up on dialogue end when `audience_delta` ≥ ±2

**Done when:** the meter visibly shifts after key turns; hint chips appear on
every wheel; delta chips animate in for significant turns.

### Step 11: Settings menu + reduce motion

- Build `<SettingsMenu>` dialog
- Typewriter speed, auto-advance, reduce motion options
- Persist to localStorage
- Wire reduce-motion to a CSS class on `<html>`

**Done when:** can change typewriter speed to Instant and have all subsequent
dialogue appear all at once.

### Step 12: Save / resume

- localStorage stores `currentSessionId`
- On title screen, if a session exists server-side, "Continue Run" is
  enabled and routes back to `/play/{id}`
- On page load of `/play/{id}`, fetch state — if 404, redirect to title

**Done when:** can refresh `/play/{id}` and resume where left off.

### Step 13: Playwright tests + screenshot smoke

- See `phase3-acceptance-and-testing.md` for the full test plan
- Add `web/tests/e2e/*.spec.ts` covering title, new-run, ceremony, finale,
  full playthrough
- Add focused browser contract tests for action reachability, duplicate-key or
  console warnings on repeated memories, long ceremony scroll behavior, and
  event overlays that should not display stale pairings.
- Add `web/tests/smoke/snapshot-pages.spec.ts` that screenshots every page
  state and saves to `web/tests/snapshots/` for visual review

**Done when:** `npx playwright test` is green and produces a set of
screenshots covering every screen.

### Step 14: Manual interactive verification

- Codex uses the Chrome extension to actually play the game from the
  checkpoints listed in `phase3-acceptance-and-testing.md`
- Screenshots and confirmation that each screen looks and feels right
- Bug list filed for any issues found

**Done when:** the acceptance criteria in `phase3-acceptance-and-testing.md`
are all met and screenshots prove it.

## 12. Risks and mitigations

- **SSE complexity** — fallback: render dialogue all-at-once after request
  completes; typewriter becomes a CSS animation over already-complete text.
  Mitigation: keep SSE as Step 6 (after non-streaming version works); don't
  block earlier steps on it.
- **Engine concurrency** — FastAPI is async but engine is sync; calls block
  the event loop. Mitigation: run engine calls in a `run_in_executor` thread
  pool. Single-user MVP so contention isn't real.
- **Browser perf with large memory lists** — virtualize the memories list if
  it gets long. Mitigation: cap displayed memories to ~20 in MVP; full
  list is in the popout.
- **Color contrast** — design tokens need to pass WCAG AA. Mitigation: run
  the contrast checker in the design-system doc and adjust if any pair fails.
- **Real-LLM cost during dev** — every turn costs a few cents. Mitigation:
  add a "mock-LLM" toggle in the FastAPI server (env var
  `PARADISE_MOCK_LLM=1`) so dev iteration is free.
