# Phase 3 — Paradise Hearts Design System

Visual and motion language for the Player UI. The look extends what's already
established in the review packet (`src/game/reporting/slides/css.py`) but
shifts from "editorial review tool" to "prestige reality TV" — a more
theatrical stage feel while keeping the same warmth.

**Vibe target:** prestige reality TV documentary. Letterboxed, warm, restrained
motion, lets the writing breathe. Not anime VN (too playful), not Hades (too
high-action), not Tinder (too techy).

**Brand vocabulary** is locked in `paradise-hearts-glossary.md` — every
UI string uses those terms (Heartbreakers, Sunset Bay, Heart Throb, Flush
of Hearts, Heart Swap, First Spark, Pulse, Heart Beats, Paradise Calls,
Heart Out, cooled on, etc.). Reference the stress-test paragraph at the
bottom of the glossary doc for tone.

## Color tokens

Defined as CSS custom properties on `:root` in `web/styles/tokens.css`. All
component styles reference these — no hard-coded colors anywhere else.

```css
:root {
  /* Surfaces */
  --bg:           #1c1612;  /* warm near-black; game stage backdrop */
  --bg-elev:     #251d18;  /* lifted surface (e.g., dialogue box rim glow) */
  --card:         #faf6ef;  /* cream; dialogue boxes, popouts, recap modals */
  --card-alt:     #fffaf2;  /* hover state, secondary card surfaces */
  --line:         #e3d8c5;  /* subtle border on cards */
  --line-strong:  #cdbfa6;  /* stronger border on feature cards */

  /* Ink */
  --ink:          #2a2620;  /* body text on cream cards */
  --ink-on-dark:  #faf6ef;  /* body text on dark stage background */
  --muted:        #786a58;  /* secondary text on cream */
  --muted-on-dark:#a99887;  /* secondary text on dark */
  --faint:        #a99887;  /* tertiary text, hints */

  /* Brand + signals */
  --accent:       #b9502f;  /* burnt orange; primary actions, player choices */
  --accent-soft:  #f6dccf;  /* selected/highlight bg */
  --accent-glow:  rgba(185,80,47,0.4);
  --sage:         #5b7c4f;  /* trust signals, Pulse+ */
  --gold:         #c8932a;  /* Pulse meter, accolades, Heart Beats */
  --gold-soft:    #f4e3b8;
  --good:         #2d6a3f;  /* success, +affection deltas */
  --bad:          #a93826;  /* miss, Heart Out, Pulse− */
  --bad-soft:     #f7e2dd;

  /* Mood tints (subtle background tints for portrait flashes) */
  --mood-happy:   rgba(91,124,79,0.18);
  --mood-flirty:  rgba(185,80,47,0.18);
  --mood-anxious: rgba(120,106,88,0.18);
  --mood-cold:    rgba(63,107,106,0.18);
  --mood-angry:   rgba(169,56,38,0.18);

  /* Shadows */
  --shadow-sm:    0 2px 8px rgba(0,0,0,0.12);
  --shadow-md:    0 8px 24px rgba(0,0,0,0.18);
  --shadow-lg:    0 16px 48px rgba(0,0,0,0.28);
  --shadow-stage: 0 24px 80px rgba(0,0,0,0.5); /* overlay drop */

  /* Radius */
  --r-sm: 6px;
  --r-md: 10px;
  --r-lg: 14px;
  --r-xl: 20px;
  --r-pill: 999px;

  /* Spacing scale */
  --s-1: 4px;
  --s-2: 8px;
  --s-3: 12px;
  --s-4: 16px;
  --s-5: 24px;
  --s-6: 32px;
  --s-7: 48px;
  --s-8: 64px;
}
```

### Contrast targets (WCAG AA)

| Pair | Contrast | Status |
|---|---|---|
| `--ink` on `--card` | 12.4:1 | passes |
| `--muted` on `--card` | 4.8:1 | passes |
| `--ink-on-dark` on `--bg` | 13.1:1 | passes |
| `--accent` on `--card` | 4.6:1 | passes |
| `--accent` on `--bg` | 4.2:1 | passes (large/AA) — for small text on dark, use cream instead |

Codex must verify with the Chrome a11y inspector during step 14.

## Typography

Three faces, loaded via `next/font`:

```ts
// web/app/layout.tsx
import { Charter, Inter, Caveat } from 'next/font/google';
// (Charter from a self-hosted file if Google Fonts doesn't carry it —
//  fall back to 'Iowan Old Style', 'Georgia', serif)
```

```css
:root {
  --font-display: 'Charter', 'Iowan Old Style', 'Georgia', serif;
  --font-body:    'Inter', -apple-system, 'Segoe UI', system-ui, sans-serif;
  --font-hand:    'Caveat', 'Comic Sans MS', cursive;
}
```

### Type scale

| Token | Size | Weight | Line height | Use |
|---|---|---|---|---|
| `--text-hero` | 72px | 700 | 1.1 | Title-screen wordmark, finale outcome |
| `--text-h1` | 36px | 600 | 1.2 | Ceremony titles |
| `--text-h2` | 24px | 600 | 1.25 | Scene headers, NPC names in dialogue |
| `--text-h3` | 18px | 600 | 1.3 | Card headers, ceremony beat lines |
| `--text-body-lg` | 18px | 400 | 1.55 | Dialogue body |
| `--text-body` | 15px | 400 | 1.5 | UI body, recap items |
| `--text-small` | 13px | 400 | 1.45 | Meta text, hints |
| `--text-tiny` | 11px | 600 | 1.3 | Chip labels, status badges |

### Usage

- **Charter** for: title wordmark, ceremony titles + narrator prose, NPC name
  tags in dialogue, finale outcome headline. Anything theatrical or "title
  card"-feel.
- **Inter** for: all body, dialogue lines, choice button labels, UI chrome,
  recap text, stats. Default.
- **Caveat** for: Paradise Calls producer-text messages, the typing-out
  flourish when "Paradise Calls" appears at the top of the stage. Used
  sparingly — these moments should feel distinct.

## Iconography

- **Lucide React** for all UI chrome (`<Menu>`, `<X>`, `<Settings>`,
  `<ChevronRight>`, `<Heart>`, `<Sparkles>`, etc.). Stroke width 1.5,
  size 20px default.
- **Emoji** for in-fiction scene/action chips (preserves the review-packet
  vocabulary):
  - 💬 Conversation
  - 🎯 Challenge
  - ✨ Ceremony
  - 🔔 Gather / Paradise Calls
  - 👥 Background
  - 🚶 Movement
  - ☀ Ambient
  - 🌅 Day boundary
  - 🏆 Finale
- **Custom inline SVG** for stat icons:
  - ♥ affection (filled, accent color)
  - ⚡ chemistry (bolt)
  - 🤝 trust (handshake — or sage circle with check)
  - 🎭 banter (theater masks)
  - 💪 graft (flex)
  - 🧠 EQ (brain)
- **Pulse meter:** 5-dot gauge inline at top bar. Each dot is a CSS circle;
  filled dots use `--gold`, empty dots use `--muted` at 30% opacity. Color
  shifts to `--sage` for very high perception, `--bad` for very low.

## Visual primitives

### `<Avatar>`

Colored circle with 2-letter initials. Color is deterministic from the
character's ID (same algorithm as `slides/cast.py`). Sizes:

- `xs` — 22px (inline in couple rows)
- `sm` — 30px (cast grid tiles)
- `md` — 44px (popout dialog header)
- `lg` — 80px (cast popout body)
- `xl` — 200px (stage portrait)

For player: `id="you"` → consistent teal-green color, initials "YO".

### `<Pill>`

Small label chip. Variants:

- `default` — cream bg, line border
- `accent` — accent-soft bg, accent border
- `success` — sage-tinted bg
- `bad` — bad-soft bg
- `gold` — gold-soft bg
- `outline` — transparent bg, line border only

### `<Button>`

Variants:

- `primary` — accent bg, cream text, slight glow on hover
- `secondary` — outline (line border, transparent), accent text on hover
- `ghost` — no bg, accent text, underline on hover
- `disabled` — muted bg, faint text, no hover

States: hover (slight lift `translateY(-1px)` + glow), active (no lift),
disabled (no interaction), loading (spinner inside).

### `<Card>`

Cream surface with line border and `--r-md` radius. Variants:

- `default` — cream bg
- `elevated` — `--shadow-md`, slight gradient `to-bottom` from `--card` to
  `--card-alt`
- `feature` — for ceremony cards: `--shadow-lg`, `--line-strong` border,
  `--r-lg` radius, more padding

### `<DialogueBox>`

Special compound: name tag (Charter, accent color, sm) above body text
(Inter, body-lg, ink). Cream card with subtle outer glow tying it to the
scene. "⟶" indicator (Lucide `<ChevronRight>`) fades in when text complete.

### `<ChoiceButton>`

Specialized button for the wheel. Layout:
```
┌──────────────────────┐
│ [+ hint chip]        │
│  Ask deeper          │
│  low · EQ            │
└──────────────────────┘
```
- Border: 1px `--line`, transitions to `--accent` on hover
- Hint chip top-left: `+` = sage, `−` = bad-soft, none = empty
- On click: locks (faded peers, full opacity on this one) until response arrives

## Motion

CSS transitions only. No animation library. Durations:

- **Fast (interaction):** 120ms — hover, button press, toggle
- **Standard (state change):** 250ms — card lift, panel toggle, dialogue fade
- **Slow (mood / ceremony):** 600ms — scene transitions, ceremony reveal,
  Pulse meter shift
- **Dramatic (one-time):** 1200ms — finale wordmark fade-in, Heart Throb
  arrival

Easing: `cubic-bezier(0.4, 0, 0.2, 1)` (Material standard) for in-out;
`cubic-bezier(0, 0, 0.2, 1)` (decelerate) for entrances.

### Specific motion patterns

**Typewriter:** characters appear at ~30 cps (Normal speed); Slow = 18 cps,
Fast = 55 cps, Instant = no delay. CSS-driven via opacity transition + JS
character feed.

**Mood flash on portrait:** background tint of portrait container shifts to
the mood color for 200ms, fades back over 600ms. Subtle — should be felt
more than seen.

**Pulse meter shift:** when `public_perception` changes, the filled dots
animate (gold/empty transition) over 600ms with easing. Numeric delta chip
(`+3`, `−2`) floats up from the meter, fades after 1500ms.

**Delta chips (`+2 affection`):** in dialogue outcome area, chips slide up
12px and fade in over 250ms; sit for 1500ms; fade out over 400ms.

**Scene transition (location change):** 300ms crossfade of background +
portrait. Dialogue box stays mounted, content swaps with typewriter.

**Ceremony entry:** stage dims to 30% opacity over 400ms, overlay fades in
from 0 to 100% over 600ms, narration prose typewrites in (slow), couples
list reveals one per row with 600ms stagger.

**Heart Throb arrival** (special ceremony case): bigger portrait fades in
at 1.2x scale → 1.0x over 1200ms with a slight slide up. Audio cue would go
here when audio is added.

**Reduce motion:** when `prefers-reduced-motion: reduce` matches OR the
settings toggle is on:
- All transitions become instant (or capped at 80ms for state legibility)
- No float-up chips; instead, deltas appear in place
- No typewriter; full text renders immediately
- No portrait scale; just fades

## Layout

### Stage breakpoints

- **Target:** 1280×800 minimum, optimized for 1440×900
- **Min supported:** 1024×768 (everything still works, tight)
- **Mobile:** explicit non-goal for MVP

### Stage grid

```
┌─────────────────────────────────────────────────────┐
│ Top bar (56px fixed)                                │
├─────────────────────────────────────────────────────┤
│                                                ┌──┐ │
│                                                │  │ │
│  Stage area (flex-1, min-height: 320px)        │  │ │
│                                                │R │ │
│                                                │a │ │
│                                                │i │ │
│                                                │l │ │
├────────────────────────────────────────────────│  │ │
│                                                │  │ │
│  Dialogue box + choices (~30% viewport height) │  │ │
│                                                │  │ │
└────────────────────────────────────────────────┴──┘ │
```

Right rail is `position: fixed` to the right edge, slides in 320px when open.

### Ceremony overlay

Full viewport coverage, dim backdrop with `backdrop-filter: blur(8px)`.
Content centered, max-width 640px, Charter prose centered.

### Dialog popouts (NPC detail, settings)

Modal: 90vw max-width 520px, max-height 80vh, scroll within. Backdrop
darkens with blur.

## Backgrounds (location gradients)

Until real art exists, each villa location is a CSS gradient. The current
character of the location should still come through.

```css
.location-pool      { background: linear-gradient(180deg, #4a8fb8 0%, #2d6585 80%, #1f4a63 100%); }
.location-kitchen   { background: linear-gradient(180deg, #d4a456 0%, #a07232 70%, #6b4d22 100%); }
.location-terrace   { background: linear-gradient(180deg, #b5c298 0%, #8aa370 70%, #5d7349 100%); }
.location-bedroom   { background: linear-gradient(180deg, #b58a8f 0%, #815f64 70%, #4d3a3d 100%); }
.location-firepit   { background: linear-gradient(180deg, #1f1410 0%, #4a1a0e 50%, #802814 90%); }
.location-suite     { background: linear-gradient(180deg, #2e1b2c 0%, #4d2840 70%, #7a3c61 100%); }  /* Paradise Suite */
.location-casa-pool { background: linear-gradient(180deg, #5a4490 0%, #3f2f6a 70%, #1f163a 100%); } /* Flush of Hearts pool (Sirens' Cove) */
```

Plus a subtle film-grain overlay (a faint noise PNG at 4% opacity) for
"prestige" feel. Generated CSS pattern, no external asset needed.

## Sound design (not in MVP, but design tokens reserved)

Define sound categories now so when audio lands we have semantic names:

- `sfx.click` — choice button click
- `sfx.text` — Paradise Calls "ding"
- `sfx.pulse.up` / `pulse.down` — Pulse meter chimes
- `sfx.ceremony` — dramatic swell
- `bgm.pool`, `bgm.firepit`, `bgm.bedroom`, etc. — location loops
- `bgm.ceremony` — drone underscore for ceremony overlay

MVP UI has volume sliders that route to no-op handlers. Phase 4+ adds files.

## Accessibility

- Every interactive element has an accessible name (button label or
  `aria-label`)
- Focus visible: 2px `--accent` outline with 2px offset
- Keyboard: Tab order matches visual order; choice buttons are reachable;
  Enter/Space activates; Esc closes dialogs and exits ceremony overlay
- Screen reader: dialogue uses `aria-live="polite"` so the text is read as
  it streams (one line per typewriter completion, not per character)
- `prefers-reduced-motion` respected (see Motion section)
- Color is never the only signal — Pulse hints have `+`/`−` symbols, not
  just color tint

## Component spec quick reference

For codex during implementation:

| Component | Key props | Notes |
|---|---|---|
| `<TopBar>` | `dayState`, `pulseScore`, `onMenuClick`, `onSettingsClick` | Sticky, 56px |
| `<DialogueBox>` | `speaker`, `text`, `streamingId?`, `onFastForward` | Auto-streams if streamingId |
| `<ChoiceMenu>` | `options[]`, `onChoose`, `locked?` | Renders ChoiceButton list |
| `<ChoiceButton>` | `option`, `onClick`, `locked`, `highlighted?` | Hint chip + label + meta |
| `<PulseMeter>` | `score`, `recentDelta?` | 5-dot gauge + floating delta |
| `<CeremonyOverlay>` | `ceremonyKind`, `narration`, `couples?`, `onContinue` | Full-screen dim+overlay |
| `<RightRail>` | `state`, `onOpenCastPopout`, `defaultOpen?` | Collapsible |
| `<CastPopout>` | `npcId`, `onClose` | Fetches detail on open |
| `<DayRecap>` | `recaps[]`, `pulseBoard`, `onContinue` | Modal overlay |
| `<FinaleScreen>` | `finaleState`, `onNewRun` | Full-screen, gold palette |
| `<Avatar>` | `id`, `name`, `size`, `mood?` | Mood adds bg tint |
| `<Button>`, `<Pill>`, `<Card>`, `<Dialog>` | standard | Reused everywhere |

## Don'ts

- Don't introduce a CSS-in-JS library (Tailwind covers it)
- Don't bring in Framer Motion / GSAP / Lottie (CSS is enough for MVP)
- Don't add a portrait library or character builder — circles are fine
- Don't introduce a new color outside the tokens
- Don't use uppercase-only headings as a design statement
- Don't animate things that don't need animating (subtle > flashy)
- Don't add a "score" or "progress bar" that doesn't exist in the engine
- Don't invent new game vocabulary not in the glossary
