# Scene-Dialogue Stage — Implementation Handoff

**Status:** docs landed (this PR); implementation NOT started.
**Owner of implementation:** codex (with Claude reviewing the merge).
**Base commit:** `c7ef42f Game-feel polish: ChallengeSpectacle, mobile drawer, finale, kiss-wed-pass bug fix`.

This document is the contract between the spec and the PR codex will write. If something is ambiguous, the answer is in the **Decisions locked** table; if the answer is not there, ask before guessing.

---

## 0. What we're building, in one paragraph

Replace the current dashboard-style UI (left panel = dialogue, right panel = choice menu, idle = CastRing) with a **mobile-first staged scene**: the resort background fills the screen, the player's character stands in the foreground bottom-center, NPCs stand in the environment, dialogue appears as **speech bubbles anchored to whoever is talking**, and player response options appear as **bubbles near the player's character**. Tapping anywhere advances long dialogue (split into consecutive bubbles). When the player picks who to talk to, the chosen NPC **walks/zooms forward**, the rest dim and recede. The same scene grammar carries through minigames: characters enter, perform, exit; the host/narrator speaks as a distinct **top-anchored narrator bubble**; the player's choices stay anchored to the player. Existing engine actions/contracts are unchanged — this is a pure renderer rewrite.

---

## 1. Decisions locked

| # | Decision | Value | Why |
|---|----------|-------|-----|
| 1 | Rollout | **Hard replace.** Delete `GameStage.tsx`'s dashboard branch entirely; ship `SceneDialogueStage` as the only stage. No feature flag. | Cleaner; no flag debt. |
| 2 | Minigames | **Wrapped in scene.** Keep `ChallengeSpectacle.tsx` as the *board layer* (quiz card, pulse matrix, detector readout) but render it **inside the scene with camera cuts**: narrator bubble top, host/contestants standing in the scene, player choices anchored to player, characters animate in/out per round. | User: "this is where the camera movement comes in". |
| 3 | Player image scope | **Per-archetype × gender = 6 images.** Archetypes: `heartthrob`, `class_clown`, `loyal_friend`. Genders: `man`, `woman`. | Existing UI only exposes those 3 archetypes (web/app/new-run/page.tsx:13–15). |
| 4 | Background removal | **Codex generates cutouts** (rembg or image-gen tool) and replaces in-place at `web/public/images/characters/*.webp`. Verify each cutout visually before committing. | User: "codex will do this … just tell codex to do it and confirm it works and looks good". |
| 5 | Narrator bubble | **Top-anchored, visually distinct** (italic serif, parchment background, no avatar) vs. character bubbles (rounded, anchored to speaker, avatar tail). | User: "narrator should be a bubble at the top of the screen and look different". |
| 6 | Tap-to-advance | **Tap anywhere on the stage** advances the current bubble. Long dialogue paginates into consecutive bubbles (one bubble = one logical chunk). When choices are visible, taps outside the choice fan are inert. | User: "you click anywhere on the screen". |
| 7 | Player always visible | **Always-on player tile at bottom-center**, including during NPC dialogue and minigames. The player tile is the anchor for response-option bubbles. | User: "I can see my character at the bottom and other character above". |
| 8 | Desktop | **Same layout on desktop.** Scale up, don't redesign. Mobile-first means mobile-correct first; desktop gets the same scene composition with larger character sprites and wider bubbles. | Simpler; one renderer. |

---

## 2. Required research before coding (step 0)

The user explicitly asked codex to study a reality dating show mobile game more before implementing:

> "for pulse we should see like a cut scene of the thing happening where it shows the characters interacting and the come into the screen and go away maybe you need to research a reality dating sim more and make it more like that. it works clearly as it's very popular"

**Codex must, before writing code:**

1. Find 2–3 gameplay videos of a reality dating show mobile game covering: a free-time conversation scene, a Pairing Ceremony/Flame Deck scene, a minigame/challenge cutscene.
2. Capture 6–10 reference screenshots into `docs/scene-dialogue/reference/` (clearly labelled, with timestamps and source link in a `reference/SOURCES.md`).
3. Document in `docs/scene-dialogue/reference/observations.md`:
   - Bubble shape, max chars per bubble, pagination indicator
   - Character pose vocabulary (idle, talking, reacting)
   - Camera move vocabulary during conversation (zoom-to-speaker, two-shot, group reaction)
   - How choices are presented (fan, stack, list); how they animate in/out
   - How minigame cutscenes are framed (full screen vs. picture-in-picture vs. character takeover)
   - How relationship/audience deltas are surfaced in-scene

The observations doc is a hard prerequisite for step 4 (`SceneDirector` design). The PR description must link to it.

---

## 3. New / changed files (overview)

### Web (Next.js)

**New:**
- `web/components/scene/SceneDialogueStage.tsx` — top-level stage replacing `GameStage` dashboard branch
- `web/components/scene/SceneLayer.tsx` — background + parallax layer
- `web/components/scene/CharacterLayer.tsx` — places player + NPCs as positioned cutouts, handles z-order/scale/focus
- `web/components/scene/CharacterSprite.tsx` — one cutout, including pose ("idle", "talking", "reacting", "exiting") and focus state ("foreground", "midground", "dimmed", "off-screen")
- `web/components/scene/SpeechBubble.tsx` — character-anchored bubble with tail
- `web/components/scene/NarratorBubble.tsx` — top-anchored, distinct style
- `web/components/scene/ChoiceFan.tsx` — anchored-to-player option bubbles
- `web/components/scene/SceneDirector.ts` — *pure-TS state machine* that converts an engine `TurnResponse` into a queue of `SceneBeat`s (see §4)
- `web/lib/scene/types.ts` — `SceneBeat`, `CharacterPose`, `CameraShot`, `BubbleSpec`, `ChoiceFanSpec`
- `web/lib/scene/positions.ts` — deterministic positioning for 1, 2, 3, 4, 5+ visible characters
- `web/public/images/player/{archetype}_{gender}.webp` — six new player cutouts (see §6)

**Modified:**
- `web/components/stage/GameStage.tsx` — delete the dashboard branch (the `<DialogueBox/>` + `<ChoiceMenu/>` + `<CastRing/>` composition); render `<SceneDialogueStage/>` instead. IntroPanel + CeremonyOverlay + DayRecap stay (they're modal screens, not part of the always-on stage).
- `web/components/stage/ChallengeSpectacle.tsx` — refactor to be *embedded inside* `SceneDialogueStage` as a `MinigameBoard` slot rather than full-screen. Keeps theme-specific render logic; loses its own background.

**Deleted (after migration):**
- `web/components/stage/DialogueBox.tsx`
- `web/components/stage/ChoiceMenu.tsx`
- `web/components/stage/CastRing.tsx`
- `web/components/stage/NpcPortrait.tsx`

**Asset work (codex-owned):**
- `web/public/images/characters/*.webp` — re-export with backgrounds removed in-place; PNG companions follow.
- `web/public/images/player/heartthrob_man.webp`, `…_woman.webp`, `class_clown_man.webp`, `…_woman.webp`, `loyal_friend_man.webp`, `…_woman.webp` (and PNG companions).

### Engine / API

**No engine changes.** The renderer reads existing `TurnResponse` fields (`exchange.npc_dialogue`, `event_narration.prose`, `available_actions`, `state.location_id`, `state.player`, `state.heartbreakers`, `state.pending_challenge`, `state.couples`). Anything the renderer needs that isn't already serialized is a *bug in the spec* — surface it before coding.

The only allowed serializer touch:
- `src/api/serializers.py`: add `state.player.archetype_id` and `state.player.gender` to the player block of the session payload **if and only if** they aren't already there (verify via `web/lib/types.ts:Player`). If they are, no change.

### Tests

- `tests/api/test_session.py` — *no change* (engine contract unchanged).
- `web/tests/e2e/scene-dialogue.spec.ts` — new Playwright spec (see §10).
- `web/tests/e2e/mobile-polish.spec.ts` — update selectors that referenced `DialogueBox` / `ChoiceMenu` / `CastRing`.
- `web/tests/e2e/action-contracts.spec.ts` — update selectors only.
- `web/tests/e2e/no-scroll.spec.ts` — confirm scene stage still passes (it should: the scene is `position: fixed; inset: 0`).

---

## 4. SceneDirector — the contract

`SceneDirector` is the single brain that turns engine state into a paintable scene. Everything else is a dumb renderer. It lives in `web/components/scene/SceneDirector.ts` and exports:

```ts
export type SceneBeat =
  | { kind: "narrator"; text: string; sourceEventId?: string }
  | { kind: "speech"; speakerId: string; text: string; pose?: CharacterPose }
  | { kind: "reaction"; reactorId: string; pose: CharacterPose; durationMs: number }
  | { kind: "camera"; shot: CameraShot; focusIds: string[]; durationMs: number }
  | { kind: "choice_fan"; spec: ChoiceFanSpec }
  | { kind: "delta_pop"; subjectId: string; deltaKind: "audience" | "affection" | "loyalty"; amount: number };

export type CameraShot =
  | "wide_group"        // everyone in scene, idle layout
  | "two_shot"          // player + one NPC, both forward
  | "speaker_focus"     // single NPC forward, player midground
  | "narrator_full"     // wide group, dimmed, narrator bubble dominates
  | "minigame_board"    // ChallengeSpectacle takes center, characters around
  | "cutscene"          // off-stage characters animate through (pulse race, flush of hearts arrival)
  ;

export type CharacterPose =
  | "idle"
  | "talking"
  | "listening"
  | "reacting_good"
  | "reacting_bad"
  | "exiting"
  | "off_stage"
  ;

export function planScene(
  prev: SessionState | null,
  next: SessionState,
  lastTurn: TurnResponse | null,
  availableActions: AvailableAction[],
): SceneBeat[];
```

**Rules:**
- `planScene` is **pure**: same inputs → same beats, no `Date.now()` / `Math.random()`.
- Beats run sequentially; each beat has either an explicit `durationMs` or "waits for tap".
- `speech` / `narrator` beats wait for tap before the next beat fires.
- `camera` / `reaction` / `delta_pop` are time-bounded (auto-advance).
- A `choice_fan` beat ends the sequence; the next `planScene` call happens after the player submits an action.
- Long `exchange.npc_dialogue` gets paginated by `paginateBubble(text)` in `web/lib/scene/pagination.ts` — paragraphs first, then sentence-pack to ≤ `MAX_BUBBLE_CHARS = 180` (revise after reality dating sim reference observations land).

**Minigame mapping** (per pending_challenge.kind):

| Kind | Opening cut | Per-round cuts | Wrap cut |
|------|-------------|----------------|----------|
| `compatibility_quiz` | `wide_group` → host enters → `narrator_full` reads stem → `two_shot` (player + round target) | `speaker_focus` on target → `choice_fan` → `delta_pop` + `reacting_*` on target | `wide_group` reaction beats per round, then board recap |
| `couples_quiz` (couples quiz) | Booth cutscene: `narrator_full` "soundproof booth" → swap to `speaker_focus` on partner | Partner's recorded answer floats in as a *replay bubble* (distinct style) → `choice_fan` → reveal | Couples align side-by-side, score pops |
| `pulse_race` | Reveal montage: each non-player struts forward briefly (`cutscene`) → `narrator_full` sets up guess | `speaker_focus` on each candidate as bubble preview → `choice_fan` (player picks) → reveal pose | Pair-up reveal |
| `lie_detector` | Sensor pads close-up insert (`cutscene`) → `narrator_full` | NPC delivers a statement (`speaker_focus`) → `choice_fan` truth/spin/bald-faced → needle insert | Aggregate score |
| `kiss_wed_pass` | Card stack cutscene → host (`narrator_full`) | Card flip per NPC; `choice_fan` is just three options | Player's three pairings shown |
| `final_couples` | Facet eyebrow (`narrator_full`) → `two_shot` per facet round | `speaker_focus` + `choice_fan` | Final tally pose |

All theme-specific *board* rendering stays in `ChallengeSpectacle` and is mounted as a child of `SceneDialogueStage` when `camera.shot === "minigame_board"`.

---

## 5. Positions and layout

`web/lib/scene/positions.ts`:

```ts
// Stage coordinates are 0..100 in both axes. Renderer scales to viewport.
// y=100 is the bottom edge; the player tile centers near y=88, scale 1.0.
export const PLAYER_ANCHOR = { x: 50, y: 88, scale: 1.0 };

export function npcPositions(count: number, focusedIndex: number | null): Position[];
```

Required layouts (renderer must look correct for each):

| count | wide_group (no focus) | speaker_focus (focus = i) |
|-------|------------------------|---------------------------|
| 1 | one at (50, 55) | (50, 50, scale 1.1) |
| 2 | (35, 55), (65, 55) | focused → (45, 50, 1.1); other → (75, 60, 0.85, dimmed) |
| 3 | (28, 55), (50, 52), (72, 55) | focused → (40, 50, 1.1); rest spread right at 0.8 scale, dimmed |
| 4 | (24, 56), (42, 53), (58, 53), (76, 56) | focused → (38, 50, 1.1); rest tucked right, 0.78, dimmed |
| 5+ | spread evenly y∈[53,57] x∈[22,78], all 0.9 scale | focused at (38, 50, 1.1); rest as a clump on right at 0.75, dimmed |

The player tile stays at `PLAYER_ANCHOR` in every layout. NPCs never overlap the player tile's footprint.

**Speech bubble anchors:**
- NPC bubble: tail points from bottom-center of the bubble to a point 8% above the character's head. Bubble lives above and slightly left/right of the character based on stage half.
- Player bubble (during scripted player lines): tail points to top of player tile. Bubble sits just above player, never overlapping ChoiceFan.
- Narrator bubble: full-width-minus-32px strip at the top, no tail, italic serif, lower opacity backdrop.

**Choice fan:**
- Renders to the immediate right of and above the player tile (mobile portrait), or as a horizontal arc above the player (desktop).
- Max 4 options visible; if >4, render as a vertical scroll-stack with subtle top/bottom fade.
- Tap target ≥ 44×44 px.
- Selecting an option: that option animates into a player bubble at `PLAYER_ANCHOR`, then the NPC reacts (next beat).

---

## 6. Character assets

### NPC cutouts (codex generates)

All existing files at `web/public/images/characters/*.webp` and `*.png`:
- `blake_start`, `chloe`, `ellis_ht`, `jordan_start`, `liam`, `marcus_start`, `maya`, `nia_start`, `riley_ht`, `sam_ht`, `sophie_start`, `talia_ht`

For each: produce a clean transparent cutout (alpha channel), preserve the existing pose, light rim/soft drop shadow baked in for scene readability. Replace in place. Keep the PNG companion. Acceptance: open each at `web/public/images/characters/<id>.png` over a black background — no white seam, no hard edges, no missing limbs.

### Player cutouts (codex generates new)

Six new files at `web/public/images/player/`:

| archetype | gender | filename |
|-----------|--------|----------|
| heartthrob | man | `heartthrob_man.webp` (+ .png) |
| heartthrob | woman | `heartthrob_woman.webp` |
| class_clown | man | `class_clown_man.webp` |
| class_clown | woman | `class_clown_woman.webp` |
| loyal_friend | man | `loyal_friend_man.webp` |
| loyal_friend | woman | `loyal_friend_woman.webp` |

Style requirements:
- Three-quarter view, full body or knees-up
- Same warm resort lighting as existing NPC photos
- Transparent background
- Visually distinct per archetype (heartthrob = confident lean, class_clown = bright open posture, loyal_friend = grounded relaxed)
- Visually distinct per gender
- ~992×1586 portrait resolution to match existing assets

The renderer picks the sprite via `playerSprite(state.player.archetype_id, state.player.gender)` in `web/lib/scene/player-sprite.ts`. Falls back to `heartthrob_man.webp` if missing (loud `console.warn` so we catch it).

---

## 7. Animation and transitions

Use Framer Motion (already in deps — verify in `web/package.json` before assuming). If not, add `framer-motion` and document why.

**Required motion vocabulary** (each lives as a named variant):

| Motion | Trigger | Spec |
|--------|---------|------|
| `enter_stage` | character appears in scene | fade in + slide up from y+8 over 320ms ease-out |
| `walk_forward` | NPC becomes focus | translate to focus position + scale to 1.1 over 360ms ease-in-out |
| `walk_back` | NPC loses focus | translate to layout position + scale to 0.85 + opacity 0.6 over 320ms |
| `bubble_pop` | speech/narrator bubble appears | scale 0.92 → 1.0 + opacity 0 → 1 over 180ms ease-out |
| `bubble_paginate` | bubble text advances | crossfade text content 120ms; bubble doesn't move |
| `choice_settle` | choice fan appears | stagger children 60ms each, slide up from y+12 |
| `choice_select` | player taps a choice | tapped choice fades + scales to bubble form, others fade out 160ms |
| `delta_pop` | audience/affection chip | y -16, fade out 800ms, anchored to subject head |
| `reacting_good` / `reacting_bad` | reveal beat | quick rotate ±3° + scale 1.04 → 1.0 over 280ms |
| `exit_stage` | character leaves scene | slide to nearest edge + fade out 320ms |
| `camera_cut` | shot change | crossfade layout 240ms; no motion blur |

Honor `prefers-reduced-motion`: all of the above collapse to 60ms opacity-only fades. Test in §10.

---

## 8. Bubble pagination

`web/lib/scene/pagination.ts`:

```ts
export function paginate(text: string, maxChars: number = MAX_BUBBLE_CHARS): string[];
```

Rules:
1. Split on paragraph boundaries (`\n\n`).
2. For each paragraph, split into sentences (`/(?<=[.!?])\s+/`).
3. Greedy-pack sentences into pages, never exceeding `maxChars`.
4. If a single sentence exceeds `maxChars`, soft-wrap on clause boundaries (`,` `;` `—`).
5. Never produce an empty page; never break inside a markdown bold/italic span (no markdown is supported in bubbles today — verify).

`MAX_BUBBLE_CHARS` starts at **180** and is revisited after the reality dating sim reference observations land. The constant lives in `web/lib/scene/pagination.ts`, NOT inlined.

---

## 9. Engine-state read map (renderer cheatsheet)

Source of truth: `web/lib/types.ts`. Renderer reads ONLY these fields. If anything needed isn't here, it's a spec bug — surface it before coding.

| What scene needs | From engine |
|------------------|-------------|
| Background image | `state.location_id` → `ResortBackground` keeps its current mapping |
| Player sprite | `state.player.archetype_id` + `state.player.gender` |
| Visible NPCs | `state.heartbreakers` (filter to `present === true`, exclude `id === state.player.id`) |
| Active speaker | `lastTurn.exchange.npc_id` (when `exchange` present) |
| NPC dialogue | `lastTurn.exchange.npc_dialogue` |
| Player line in-scene | `lastTurn.exchange.player_line` (rendered as a player bubble before the NPC bubble) |
| Narrator prose | `lastTurn.event_narration.prose` |
| Pending choices | `availableActions` (from `useAvailableActions`) |
| Pending minigame | `state.pending_challenge` |
| Per-round result | `state.pending_challenge.answered_rounds[]` |
| Audience delta pop | `lastTurn.audience_delta` + `lastTurn.audience_delta_reason` |
| Affection delta pop | `lastTurn.affection_changes[]` (verify field name; if not present, skip for v1) |
| Couple status (for two_shot framing) | `state.couples` |

---

## 10. Success criteria and tests

A PR is mergeable when **all** of the following hold. The PR description must reference each.

### Must pass (automated)

1. `uv run pytest tests/ --ignore=tests/agents` — 368+ tests pass (engine unchanged → no regressions).
2. `cd web && npx tsc --noEmit` — clean.
3. `uv run python -m src.game.cli verify --all` — all fixture hashes still pass.
4. `cd web && npx playwright test` — all e2e specs pass, including new ones below.
5. `cd web && npx next build` — production build succeeds.

### New e2e coverage (`web/tests/e2e/scene-dialogue.spec.ts`)

- `idle scene shows player + all present NPCs` — load a bundled checkpoint at day-1 morning; assert `[data-testid="character-sprite"]` count = heartbreakers + 1; player sprite has `data-role="player"`; player has `data-position="bottom"`.
- `NPC speaks → bubble anchored to NPC` — start a conversation; assert speech bubble's `data-anchor-id` matches the NPC id; assert bubble is above the NPC sprite.
- `narrator beat → narrator bubble at top, no character bubble` — trigger any `gather_scheduled` event; assert `[data-testid="narrator-bubble"]` is visible, top-anchored, no `[data-testid="speech-bubble"]`.
- `tap anywhere advances bubble` — paginate a long line of dialogue; tap on the stage background; assert bubble text changed to the next page.
- `choice fan appears near player` — at a beat with multiple actions; assert `[data-testid="choice-fan"]` is within 40% of viewport width of the player sprite center.
- `selecting a choice animates to bubble, then NPC reacts` — pick an action; within 1000ms assert a `[data-testid="player-bubble"]` appears, then within 1500ms assert the NPC `data-pose` switches to `reacting_*`.
- `pulse race opening cutscene` — load the `day2-pre-pulse-race` checkpoint and advance; assert at least one NPC sprite has `data-pose="exiting"` within 1500ms (the strut-by cutscene fires).
- `compat quiz keeps player visible during round` — load `day1-pre-compatibility-quiz` and answer round 1; assert player sprite stays mounted with `data-position="bottom"` throughout.
- `mobile portrait (390×844): no horizontal scroll` — set viewport to iPhone 12; assert `document.body.scrollWidth <= window.innerWidth`.
- `desktop (1280×800): scene scales, player still bottom-center` — set viewport; assert player sprite center x is within 5% of 640.
- `reduced motion: long camera animations are skipped` — set `prefers-reduced-motion: reduce`; assert NPC focus change completes in < 100ms.

### Manual playtest checklist (codex must run before opening the PR; report results in the PR description)

For each of the 9 bundled checkpoints (`day1-pre-compatibility-quiz`, `day2-pre-pulse-race`, `day3-pre-couples-quiz`, `day3-pairing-ceremony`, `day4-flush-of-hearts-announce`, `day4-pre-lie-detector`, `day5-pre-kiss-wed-pass`, `day6-pre-final-couples`, `day6-pre-final-vote`):

- [ ] Stage loads without console errors
- [ ] Player sprite is visible at bottom-center
- [ ] All present NPCs visible, none clipped, none overlapping the player
- [ ] First conversational tap shows a bubble anchored to the right speaker
- [ ] Tapping background advances; tapping a choice picks it
- [ ] Selecting a choice produces a player bubble then an NPC reaction
- [ ] Narrator prose renders at top in its own style
- [ ] No horizontal scroll on iPhone 12 viewport
- [ ] Player remains visible during minigame rounds
- [ ] Camera-cut transitions look intentional, not janky

Attach **6 screenshots** to the PR: idle scene, mid-conversation, choice fan visible, narrator-bubble beat, minigame round, post-minigame wrap.

### Asset acceptance (codex self-checks before merge)

- [ ] All 12 NPC cutouts have clean alpha (open against pure black: no white seam, no hair clumps clipped)
- [ ] All 6 player cutouts are visually distinct per archetype AND per gender (eyeball test)
- [ ] No cutout file > 400 KB (webp); PNG companion < 1.2 MB
- [ ] Sprite scaling at 0.75 stays legible on a 320-px-wide viewport

### Performance budget

- First-paint on iPhone 12 (throttled "Slow 3G", cached): < 2.5s to scene visible
- Scene render p95 frame time on iPhone 12: < 16ms (one frame at 60fps)
- Memory: cutouts lazy-load — only the visible characters' images are fetched on initial render

Codex measures with `next build && npx serve out` and Chrome DevTools throttling; report numbers in the PR.

---

## 11. Things that are explicitly out of scope (v1)

- Voice acting / SFX. Bubbles are silent. (Future PR.)
- Custom character creator (hair, outfit, skin tone). The 6 player sprites are it.
- Lip-sync / talk animation on the cutouts. Pose changes only.
- Per-emotion sprite variants (one sprite per character; pose is achieved by transform + filter).
- Animated resort background. Static image stays.
- Day/night lighting shifts on cutouts. Defer.
- Sims-style action wheel. The user explicitly rejected it for conversation; reserve the wheel concept for later non-dialogue actions (move location, open resort info).

---

## 12. Sequencing for codex

Recommended PR shape — submit as **one PR** (hard replace), but commit history reads chronologically so review is tractable:

1. `scene-dialogue: reference research + observations doc` — adds `docs/scene-dialogue/reference/*` only.
2. `scene-dialogue: types, director, pagination, positions` — new TS files, zero rendering, with unit tests for `paginate()` and `npcPositions()`.
3. `scene-dialogue: SceneDialogueStage + CharacterLayer + bubbles (conversation only)` — wires up free-time conversation, minigames still use old ChallengeSpectacle full-screen.
4. `scene-dialogue: minigame integration` — embed ChallengeSpectacle into the scene, add per-minigame camera/cutscene sequencing.
5. `scene-dialogue: NPC cutouts (in-place replacement)` — asset commit.
6. `scene-dialogue: player cutouts` — asset commit, six new files.
7. `scene-dialogue: delete dashboard renderers + update e2e tests` — `git rm` DialogueBox, ChoiceMenu, CastRing, NpcPortrait; update specs that referenced them. Final commit makes the new stage the only stage.

Each commit must pass `npx tsc --noEmit` and `uv run pytest`. The final commit must pass everything in §10.

---

## 13. Review handoff back to Claude

When the PR is ready, codex pushes a branch and pings here. Claude reviews against this doc, runs §10's automated checks, eyeballs the 6 PR screenshots and three from each checkpoint, and either merges or sends a single round of inline feedback. Don't merge yourself; the spec author and the reviewer are different intentionally.

---

## Appendix A — File mapping reference (post-merge target)

```
web/
├── components/
│   ├── scene/                      ← new
│   │   ├── SceneDialogueStage.tsx
│   │   ├── SceneLayer.tsx
│   │   ├── CharacterLayer.tsx
│   │   ├── CharacterSprite.tsx
│   │   ├── SpeechBubble.tsx
│   │   ├── NarratorBubble.tsx
│   │   ├── ChoiceFan.tsx
│   │   └── SceneDirector.ts
│   ├── stage/
│   │   ├── GameStage.tsx           ← slimmed: only wraps SceneDialogueStage + modals
│   │   ├── ChallengeSpectacle.tsx  ← refactored as embedded board
│   │   ├── ResortBackground.tsx    ← unchanged
│   │   ├── TopBar.tsx              ← unchanged
│   │   ├── PulseMeter.tsx          ← unchanged or absorbed into ChallengeSpectacle
│   │   ├── DeltaChip.tsx           ← unchanged (re-used by delta_pop beat)
│   │   ├── IntroPanel.tsx          ← unchanged (modal, not part of stage)
│   │   ├── DialogueBox.tsx         ← DELETED
│   │   ├── ChoiceMenu.tsx          ← DELETED
│   │   ├── CastRing.tsx            ← DELETED
│   │   └── NpcPortrait.tsx         ← DELETED
│   └── …
├── lib/
│   ├── scene/                      ← new
│   │   ├── types.ts
│   │   ├── positions.ts
│   │   ├── pagination.ts
│   │   └── player-sprite.ts
│   └── …
├── public/
│   └── images/
│       ├── characters/             ← cutouts replace existing in place
│       └── player/                 ← new dir
└── tests/
    └── e2e/
        ├── scene-dialogue.spec.ts  ← new
        ├── mobile-polish.spec.ts   ← selector updates
        └── action-contracts.spec.ts ← selector updates
```

---

## Appendix B — Open questions codex should NOT decide alone

If any of these come up mid-implementation, stop and ask:

1. The engine doesn't currently emit per-NPC reaction text alongside the main `npc_dialogue` — if codex finds the scene wants reaction bubbles on side characters and they aren't in the API, **don't synthesize them client-side**. Ask, and we'll decide whether to plumb a new field.
2. If `paginate()` produces bubbles that look bad below a certain `MAX_BUBBLE_CHARS`, change the constant in code but **flag the chosen value** in the PR description with a screenshot for the next reviewer.
3. If a checkpoint produces a scene with >7 visible NPCs, the layout in §5 doesn't cover it. Ask before extending; we may want to switch to a "group panel" framing rather than spreading 8 sprites across the stage.
4. If background-removal artifacts on any NPC cutout are visible at the on-stage rendered size, ask before shipping. Better to re-generate than to ship a haloed cutout.
