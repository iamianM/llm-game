# Phase 3 — Acceptance Criteria + Testing Plan

This document defines what "done" means for the Paradise Hearts Player UI MVP
and the verification codex must do before reporting back. The standard is
**codex itself plays through the game in a real browser and confirms
everything looks and feels right** — not just that tests pass.

**All player-facing copy must use Paradise Hearts vocabulary** from
`paradise-hearts-glossary.md`. During interactive verification, codex
explicitly checks that no Love Island residue ("islanders", "villa", "Casa
Amor", "bombshell", "recoupling", "graft", "I've got a text", "dumped", etc.)
appears anywhere in the UI. Engine-internal identifiers in API payloads are
fine; only player-facing strings need to be rebranded.

## Three tiers of verification

| Tier | What | When |
|---|---|---|
| **1. Automated unit tests** | pytest for FastAPI; type-check + lint for both layers | Every commit |
| **2. Automated end-to-end (Playwright)** | Headless browser scripts covering all flows | Every commit |
| **3. Manual interactive playthrough** | Codex uses its Chrome browser tool to actually play the game from named checkpoints, takes screenshots, confirms feel | Before reporting Phase 3 done |

All three must be green before Phase 3 is reported complete.

## Tier 1 — Automated unit tests

### Backend (`tests/api/`)

- `test_session.py`
  - Create a session with each archetype → state shape valid
  - Get session by id → matches what was created
  - Get nonexistent session → 404
  - Delete session → 204, subsequent get returns 404
- `test_turn.py`
  - Submit a valid action → state updates, available_actions returned
  - Submit an invalid action → 400 with INVALID_ACTION code
  - Submit during ceremony → returns ceremony_events
  - Concurrent turns on same session → second blocks until first completes
- `test_streaming.py`
  - SSE endpoint emits all expected event types in correct order
  - Mock-LLM mode produces dialogue_chunk events with sane chunks
  - Error mid-stream → error event then close
- `test_display.py`
  - Engine event_kind "recoupling" → display "Pairing Ceremony"
  - Engine challenge "snog_marry_pie" → display "Kiss Wed Pass"
  - Every engine-side identifier has a display translation OR is explicitly
    in the passthrough allow-list (validates `DISPLAY_NAMES` coverage)

### Frontend type-check

- `npm run type-check` (tsc --noEmit) must pass
- `npm run lint` (ESLint + Prettier) must pass

### Both

- `make qa` must remain green (existing 320+ tests)

## Tier 2 — Playwright automated E2E

Playwright lives in `web/tests/`. Configure in `web/playwright.config.ts` to
target headless Chrome by default, with the project also configured for
WebKit and Firefox (run on CI only).

```bash
# Run all Playwright tests
cd web && npx playwright test

# Run with UI for debugging
cd web && npx playwright test --ui

# Run a single suite
cd web && npx playwright test e2e/full-playthrough
```

Playwright starts FastAPI on port 8000 and Next.js on port 3000 via
`web/playwright.config.ts` `webServer` entries.

### `e2e/title.spec.ts`

- Visit `/` → wordmark "Paradise Hearts" visible
- "New Run" button enabled, clickable
- "Continue Run" and "The Reunion" disabled
- Click "New Run" → URL is `/new-run`

### `e2e/new-run.spec.ts`

- Visit `/new-run` → three archetype cards visible
- Each card shows: name, stat bonus, advantage
- Click "Heartthrob" → POST `/session/new` succeeds → URL is `/play/{uuid}`
- Same for the other two archetypes

### `e2e/full-playthrough.spec.ts` ⭐ the critical test

The big one. Plays a complete 6-day game in mock-LLM mode. Should run in
under 60 seconds.

```ts
test('complete playthrough lands on finale', async ({ page }) => {
  await page.goto('/');
  await page.click('text=New Run');
  await page.click('text=Heartthrob');
  await expect(page).toHaveURL(/\/play\/.+/);

  // Play turns until outcome is set
  while (await page.locator('[data-screen="finale"]').count() === 0) {
    // Open the first available choice (or skip ceremony)
    if (await page.locator('[data-screen="ceremony"]').count() > 0) {
      await page.click('text=Continue');
      continue;
    }
    if (await page.locator('[data-screen="day-recap"]').count() > 0) {
      await page.click('text=Continue');
      continue;
    }
    // Click the first non-locked choice button
    const choice = page.locator('[data-role="choice"]').first();
    await choice.click();
    // Wait for dialogue to complete (typewriter)
    await page.waitForSelector('[data-state="dialogue-complete"]', { timeout: 8000 });
  }

  // Finale visible
  await expect(page.locator('[data-screen="finale"]')).toBeVisible();
  await expect(page.locator('text=/Heart Beats/')).toBeVisible();
});
```

Variations: same test seeded with different archetypes; same test that picks
"highest-affection" choice every time vs "random"; same test that triggers
the recouple-proposal action when available.

### `e2e/ceremony.spec.ts`

- Resume from checkpoint `ui-day1-first-pairing` (created in step below)
- Verify the ceremony overlay is visible with the correct title ("First
  Pairing")
- Verify the couples list appears (one per row)
- Click "Continue" → returns to stage

### `e2e/finale.spec.ts`

- Resume from checkpoint `ui-day6-final-vote`
- Submit the last action
- Verify finale screen renders with winning couple, Pulse Board, and
  Heart Beats display
- Click "New Run" → returns to title

### `e2e/settings.spec.ts`

- Open settings menu
- Toggle typewriter speed to "Instant"
- Submit a turn → dialogue renders immediately (no typewriter delay)
- Toggle "Reduce motion" → CSS class applied, transitions disabled

### `e2e/rail-popouts.spec.ts`

- Toggle right rail open
- Verify Sunset Bay map, couples panel, Heartbreaker grid visible
- Click a Heartbreaker tile → popout dialog opens
- Verify backstory, relationship bars, Type on Paper, memories visible
- Close popout, close rail

### `e2e/brand-vocabulary.spec.ts` ⭐ zero-tolerance vocabulary check

Walks the full playthrough and asserts no Love Island residue appears in any
rendered page source:

```ts
const FORBIDDEN_STRINGS = [
  /\bislander/i, /\bThe Villa\b/, /\bCasa Amor\b/i,
  /\bbombshell/i, /\brecoupling\b/i, /\bgraft(ing)?\b/i,
  /I('|’)?ve got a text/i, /\bdumped\b/i,
  /\bmugged off\b/i, /\bpied\b/i,
];

test('no Love Island residue in player-facing copy', async ({ page }) => {
  // Walk through every screen
  for (const screenName of allScreens) {
    await navigateTo(page, screenName);
    const html = await page.content();
    // Strip script tags and JSON data (engine internals can use generic names)
    const visibleText = stripScriptsAndDataAttrs(html);
    for (const pattern of FORBIDDEN_STRINGS) {
      expect(visibleText).not.toMatch(pattern);
    }
  }
});
```

Codex MUST add this test, run it, and verify it passes before reporting done.

### `smoke/snapshot-pages.spec.ts` — visual smoke

For every distinct screen state, take a full-page screenshot and save to
`web/tests/snapshots/`. These are for codex (and you) to visually review.

```ts
const states = [
  { name: 'title', goto: () => page.goto('/') },
  { name: 'new-run', goto: () => page.goto('/new-run') },
  { name: 'play-day1-intros', goto: () => resumeCheckpoint(page, 'ui-day1-intros') },
  { name: 'play-day1-conversation', goto: () => resumeCheckpoint(page, 'ui-day1-conversation') },
  { name: 'play-day1-ambient', goto: () => resumeCheckpoint(page, 'ui-day1-ambient') },
  { name: 'ceremony-first-spark', goto: () => resumeCheckpoint(page, 'ui-day1-first-spark') },
  { name: 'ceremony-heart-throb', goto: () => resumeCheckpoint(page, 'ui-day3-heart-throb') },
  { name: 'ceremony-flush-of-hearts', goto: () => resumeCheckpoint(page, 'ui-day4-flush-of-hearts') },
  { name: 'recouple-proposal', goto: () => resumeCheckpoint(page, 'ui-recouple-proposal') },
  { name: 'day-recap', goto: () => resumeCheckpoint(page, 'ui-day3-recap') },
  { name: 'finale', goto: () => resumeCheckpoint(page, 'ui-day6-finale') },
  { name: 'cast-popout', goto: () => /* open popout for chloe */ },
  { name: 'rail-open', goto: () => /* open right rail */ },
  { name: 'settings', goto: () => /* open settings */ },
];

for (const state of states) {
  test(`snapshot ${state.name}`, async ({ page }) => {
    await state.goto();
    await page.waitForTimeout(500);
    await page.screenshot({ path: `web/tests/snapshots/${state.name}.png`, fullPage: true });
  });
}
```

These snapshots are reviewed visually by codex (step 14) and attached to the
PR/report. We are NOT using visual regression testing (pixel diffing) in MVP —
too brittle. The snapshots are inspection artifacts.

## Tier 3 — Manual interactive playthrough

Codex uses its Chrome browser tool to **actually play the game**. This is the
most important verification step. Automated tests confirm code paths work;
this confirms the experience is right.

### Required interactive playthroughs

Codex must do all of these before reporting Phase 3 done:

#### Playthrough A — Full fresh run (mock-LLM)

- Start FastAPI in mock-LLM mode: `PARADISE_MOCK_LLM=1 uv run uvicorn ...`
- Start Next.js dev server
- Open `http://localhost:3000` in Chrome
- Click through title → archetype → enter the villa
- Play **every turn** of Day 1 through finale
- Take screenshots at every distinct screen state
- Confirm:
  - Typewriter pacing feels natural (not too slow, not too fast)
  - All choice buttons are clickable
  - Pulse meter visibly shifts at key moments
  - Ceremony overlays look distinct from regular stage
  - Day boundary recap appears between days
  - Finale screen lands correctly
  - No JS console errors throughout

#### Playthrough B — Full fresh run (real-LLM)

- Same as A but with real OpenAI/Anthropic credentials
- Spot-check dialogue quality (does it read like character voice?)
- Confirm streaming feels alive (text genuinely appearing as the model generates)
- Confirm no streaming timeouts or stalls
- ~$5-10 in API cost; worth it for milestone validation

#### Playthrough C — Targeted checkpoint resumes (mock-LLM)

Resume from each of the checkpoints listed below, take 3+ screenshots
showing the interaction working, and confirm the specific feature renders
correctly. These exist to validate code paths that don't always trigger in
a single playthrough.

### Named checkpoints codex must validate

Codex creates these checkpoints during a full Playthrough A run, saving at
the right moments. Each checkpoint is a `play-session checkpoint` artifact
that can be resumed via `play-session resume --from-checkpoint`.

| Checkpoint name | When in the run | What it validates |
|---|---|---|
| `ui-day1-first-spark` | Right before the First Spark ceremony fires | Ceremony overlay for opening pairing; couples list animation |
| `ui-day1-intros` | After First Spark, before first intro | Intros segment: constrained menu, 7 mini-conversations |
| `ui-day1-conversation` | During first regular conversation (day 1 afternoon) | Standard conversation flow, choice menu, Pulse hints |
| `ui-day1-ambient` | When player picks an ambient action | Ambient action card, "stay" continuation, NPC encounter chance |
| `ui-day2-paradise-calls` | When a Paradise Calls producer text fires | Distinct producer-text styling (Caveat font, dramatic flourish) |
| `ui-day3-heart-throb` | When a Heart Throb arrival fires | Heart Throb arrival ceremony — bigger portrait, intro line |
| `ui-day3-pairing-ceremony` | At the Day-3 Pairing Ceremony | Multi-couple recoupling, full screen overlay |
| `ui-day3-recap` | End of Day 3 | Day boundary modal, Pulse Board |
| `ui-day4-flush-of-hearts` | Flush of Hearts announcement | Flush of Hearts intro ceremony, location shift |
| `ui-day4-flush-of-hearts-arrival` | Right after entering Flush of Hearts | Background change to Flush of Hearts color palette (Sirens' Cove) |
| `ui-day5-flush-of-hearts-decision` | Flush of Hearts return decision | Decision flow rendered as a distinct prompt |
| `ui-recouple-proposal-player` | Just before player triggers a PROPOSE_RECOUPLE | Player-initiated proposal flow, accept/reject branch |
| `ui-recouple-proposal-npc` | When an NPC proposes to the player | NPC-initiated proposal screen with three response options |
| `ui-day6-final-vote` | Right before the final vote | Finale ceremony narration, Pulse reveal |
| `ui-day6-finale` | After final vote outcome | Finale screen with winning couple, stats, HA earned |

For each checkpoint, codex:
1. Resumes the checkpoint
2. Plays forward 1–5 turns to exercise the relevant feature
3. Takes screenshots showing the feature
4. Notes any visual or interaction issues

### Cast popout validation

In any active session, codex opens the right rail, clicks each cast tile,
and verifies:
- Avatar circle with initials renders
- Backstory text present (if known)
- Relationship bars render with correct values (affection, chemistry, trust, friendship)
- Type-on-Paper section shows revealed fields based on familiarity:
  - Familiarity < 25: all fields are `???`
  - Familiarity ≥ 25: physical_type revealed
  - Familiarity ≥ 50: personality_type revealed
  - Familiarity ≥ 75: values revealed
  - Familiarity ≥ 100: dealbreakers revealed
- Memories list shows the NPC's recent memories
- Close button + click-outside both work

### Accessibility quick-check

In Chrome DevTools, codex runs:
- **Lighthouse Accessibility** audit on `/`, `/new-run`, `/play/{id}` →
  score ≥ 90
- **Keyboard nav** on the stage: Tab through all interactive elements,
  Enter activates a choice, Esc closes any open dialog
- **Reduce motion** preference set in OS → confirm transitions disabled
- **Screen reader spot-check** on dialogue: enable VoiceOver/NVDA, confirm
  NPC dialogue is announced when typewriter completes (one announcement per
  line, not per character)

### Cross-browser sanity

Open the game in:
- Chrome (primary)
- Edge (Chromium)
- Safari (if on macOS)

Spot-check: title screen renders, can start a run, can play 5 turns. No
visual breaks. Console clean.

## Acceptance criteria checklist

Before codex reports Phase 3 done, every box must be checked:

### Build / quality

- [ ] `make qa` green (Python lint, mypy, content lint, tests, smoke, determinism)
- [ ] `cd web && npm run type-check` green
- [ ] `cd web && npm run lint` green
- [ ] `cd web && npm run build` green (production build succeeds)
- [ ] `cd web && npx playwright test` green
- [ ] FastAPI starts cleanly: `uv run uvicorn src.api.app:app` shows no errors
- [ ] Next.js starts cleanly: `npm run dev` shows no errors or warnings

### Feature coverage

- [ ] Title screen renders with Paradise Hearts wordmark
- [ ] Character creation flow with 3 archetypes works end to end
- [ ] Stage screen renders all engine state (Heartbreaker portraits, location, Pulse, etc.)
- [ ] SSE streaming dialogue typewriter works
- [ ] Choice menu shows Pulse hints (+/−/empty)
- [ ] Right rail opens, all 4 sections render
- [ ] Cast popout dialog shows full NPC detail with familiarity gates
- [ ] First Spark renders as a ceremony overlay (Day 1)
- [ ] Day-1 intros segment forces the 7 mini-conversations
- [ ] Ambient actions render and can be picked
- [ ] Heart Throb arrival renders distinctly
- [ ] Day-3 Pairing Ceremony renders with multi-couple animation
- [ ] Flush of Hearts announcement + arrival render
- [ ] Flush of Hearts return decision works
- [ ] Recouple proposal (player-initiated) flow works
- [ ] Recouple proposal (NPC-initiated) flow works
- [ ] Day boundary recap modal appears between days
- [ ] Finale screen renders with all stats
- [ ] Settings menu: typewriter speed, auto-advance, reduce motion all work
- [ ] Save/resume: refresh `/play/{id}` returns to in-progress run

### Visual / feel (subjective but required)

- [ ] All screen states have a corresponding screenshot in `web/tests/snapshots/`
- [ ] No placeholder text or `TODO` strings visible to the player
- [ ] All player-facing strings use Paradise Hearts glossary terms (not
      Love Island terms)
- [ ] Typography is correct: Charter for headings, Inter for body, Caveat
      for Paradise Calls
- [ ] Color palette matches the design system tokens; no hard-coded colors
- [ ] Pulse meter visibly shifts during a real game (codex observed it)
- [ ] Ceremony overlay feels distinct from normal stage (dimmed backdrop,
      centered serif prose)
- [ ] Heart Throb arrivals feel "bigger" than normal turns (larger portrait,
      slow fade-in)
- [ ] Finale feels like an ending (gold palette, larger type, winning couple
      front and center)

### Brand vocabulary (zero tolerance for LI residue)

Codex runs a search through the rendered page source of each captured
screenshot for any of these strings — if any appear in player-facing copy,
it's a fail:

- "islander", "Islanders", "the villa", "The Villa", "Villa"
- "Casa Amor", "casa amor"
- "bombshell", "Bombshell"
- "recoupling", "Recoupling" (the action; "Pairing Ceremony" the event is OK)
- "graft", "grafting"
- "I've got a text", "ive got a text"
- "dumped", "mugged off", "pied"

Engine-internal API field names (`bombshell`, `casa_amor`, `recouple`, etc.)
in network responses are NOT player-facing and are fine.

- [ ] Zero LI-residue strings found in any rendered page source
- [ ] All Paradise Hearts vocabulary from `paradise-hearts-glossary.md` is
      surfaced where appropriate (Heartbreakers, Sunset Bay, Heart Throb,
      Flush of Hearts, Heart Swap, First Spark, Pulse, Heart Beats, Paradise
      Calls, Heart Out, cooled on)

### Performance

- [ ] Title screen first-paint < 1s
- [ ] Stage screen first interaction < 2s after session created
- [ ] SSE first character appears within 500ms of click
- [ ] No frame drops during ceremony transitions (60fps maintained)
- [ ] No memory leak after 100+ turns (manual: play A then watch DevTools memory)
- [ ] No console errors or warnings during normal play

### Accessibility

- [ ] Lighthouse Accessibility score ≥ 90 on all main routes
- [ ] Keyboard nav works through every screen
- [ ] Focus visible on all interactive elements
- [ ] Reduce-motion preference respected
- [ ] Screen reader announces dialogue (spot-checked)

### Report artifacts

Codex's final report must include:

1. **Status table** mirroring the checklist above (all boxes ticked)
2. **Screenshot gallery** — embed or link to all snapshots from `web/tests/snapshots/`
3. **Interactive playthrough notes** — for each named checkpoint, a 1-2 sentence
   note confirming the feature renders as designed (e.g., "ui-day3-heart-throb:
   confirmed — bigger portrait, slow fade-in, distinct from normal turns")
4. **Bugs found and fixed** — list anything that broke during interactive
   verification and how it was resolved
5. **Performance metrics** — Lighthouse score, first-paint time, any memory
   observations
6. **Known limitations** — anything codex deliberately chose to defer (each
   item must be in the existing "Out of MVP" list or explicitly approved as a
   new deferral)

## Test data and seeds

- **Default mock seed:** 42 — produces a known-good Day 1 with Chloe coupling
  and 4 NPC pairings forming opposite-gender
- **Recouple proposal seed:** TBD — codex finds a seed where chemistry hits
  threshold early; documents it for the checkpoint
- **Flush of Hearts decision seed:** the default seed should reach this; if not,
  codex documents an alternate seed

## Failure protocol

If any acceptance criterion fails:
- Codex stops, fixes, retests, repeats until green
- Does NOT report Phase 3 complete with caveats
- If a criterion is genuinely impossible to meet for a documented reason,
  codex flags it explicitly with rationale; owner decides whether to accept
  the deferral or hold the release

## Tools codex uses

- **Chrome browser tool** (the extension): for interactive playthroughs A and B,
  taking screenshots, opening DevTools, running Lighthouse
- **Playwright headless** (`npx playwright test`): for automated E2E
- **pytest** (`uv run pytest tests/api/`): for FastAPI unit tests
- **Manual Chrome on host**: as a final spot-check before reporting
