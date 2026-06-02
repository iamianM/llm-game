/**
 * Golden Playthrough — the curated showcase walk-through.
 *
 * Unlike `e2e/full-playthrough.spec.ts` (which proves the engine survives a
 * randomized 6-day run), this spec is a deterministic, hand-choreographed tour
 * of every distinct UI surface in Paradise Hearts. It captures wide-format
 * screenshots at every dramatic beat and assembles them into a slideshow
 * gallery at the end. Re-run this any time the UI changes — the gallery is
 * the canonical sizzle reel.
 *
 * Output: `web/tests/snapshots/golden/<NN>-<beat>.png` + `index.html` gallery.
 */

import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const SHOTS_DIR = path.join(process.cwd(), "tests", "snapshots", "golden");

type Beat = {
  index: number;
  file: string;
  title: string;
  caption: string;
};

const beats: Beat[] = [];
let beatIndex = 0;

async function shot(page: import("@playwright/test").Page, title: string, caption: string) {
  beatIndex += 1;
  const file = `${String(beatIndex).padStart(2, "0")}-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}.png`;
  const out = path.join(SHOTS_DIR, file);
  // Wait a beat for animations to settle without slowing the suite to a crawl.
  await page.waitForTimeout(180);
  await page.screenshot({ path: out, fullPage: false, animations: "disabled" });
  beats.push({ index: beatIndex, file, title, caption });
}

test.describe.configure({ mode: "serial" });

test.afterEach(() => {
  // Always write the gallery — even if the run was cut short, the partial
  // beats are still useful.
  if (beats.length > 0) {
    const html = renderGallery(beats);
    fs.writeFileSync(path.join(SHOTS_DIR, "index.html"), html, "utf8");
  }
});

test("Golden Playthrough · the Paradise Hearts sizzle reel", async ({ page }) => {
  test.setTimeout(360_000);
  await page.setViewportSize({ width: 1600, height: 900 });
  fs.mkdirSync(SHOTS_DIR, { recursive: true });

  // ─── 1. TITLE ──────────────────────────────────────────────
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(500);
  await shot(
    page,
    "Title",
    "Paradise Hearts — the arrival. Charter serif wordmark, gold-shimmer italic, palm silhouettes against a sunset horizon."
  );

  // ─── 2. NEW RUN ────────────────────────────────────────────
  await page.getByRole("link", { name: "New Run" }).click();
  await page.waitForLoadState("networkidle");
  // The casting screen opens on the roster: a grid of pre-made Heartbreakers with
  // the first pick highlighted and a live casting-card preview of their look.
  await shot(
    page,
    "Character select",
    "Choose your Heartbreaker. A grid of pre-made roster cards beside a live casting-card preview with outfit-graded lighting, and a 'Play as …' CTA."
  );

  // ─── 3. ENTER ──────────────────────────────────────────────
  await page.getByRole("button", { name: "Demo" }).click();
  await page.getByRole("button", { name: /^Play as / }).click();
  await page.waitForURL(/\/play\/.+/);
  // Wait for the stage HUD + initial action menu to be visible.
  await expect(page.getByTestId("choice-fan")).toBeVisible({ timeout: 15_000 });
  // Speed up animations + typewriter for the rest of the showcase.
  await page.getByLabel("Open settings").click();
  await page.getByLabel("Typewriter speed").selectOption("fast");
  await page.getByRole("dialog").getByRole("button", { name: "Close" }).click();
  await page.waitForTimeout(200);
  await shot(
    page,
    "First Spark choices",
    "Day 1, morning. The four opening pair options. The game's first decision. Pulse meter is anchored at 50, no audience reaction yet."
  );

  // ─── 4. FIRST SPARK CEREMONY ───────────────────────────────
  await page.getByRole("button", { name: "Pair with Chloe" }).click();
  await expect(page.locator('[data-screen="ceremony"]')).toBeVisible({ timeout: 15_000 });
  await page.waitForTimeout(900); // Let the couple rows animate in.
  await shot(
    page,
    "First Spark ceremony",
    "Paradise Calls · First Spark. The opening couples lock in with a staggered reveal. Gold-bordered pair rows beneath the gold-shimmer title."
  );

  // ─── 5. INTROS: FIRST NPC GREETS ───────────────────────────
  await page.getByRole("button", { name: "Continue" }).click();
  await page.waitForTimeout(400);
  // We should now be on the IntroPanel. Capture the first greeting.
  await expect(page.locator('[data-screen="intros"]')).toBeVisible();
  await shot(
    page,
    "Intros · first greeting",
    "Day-1 introductions. The first Heartbreaker walks up and greets the player. Four real-dialogue response cards beneath — Friendly, Flirty, Deep, Banter — each a line the player can actually say."
  );

  // ─── 6. INTROS: RESPONSE LANDS ─────────────────────────────
  await page.locator('[data-intent="intro_deep"]').click();
  await expect(page.locator('[data-screen="intros"][data-state="dialogue-complete"]')).toBeVisible({ timeout: 10_000 });
  await page.waitForTimeout(250);
  await shot(
    page,
    "Intros · deep response lands",
    "Player picked the Deep response. NPC mirrors back. Each bubble carries a name-tag chip above a rounded card with a tail — the player's reads warm cream, the NPC's clean white."
  );

  // ─── 7. INTROS: SECOND ARCHETYPE ───────────────────────────
  // After the response, IntroPanel will auto-advance to the next NPC on the
  // next click. We click intro_friendly to wrap that intro and reveal NPC #2.
  await page.locator('[data-intent="intro_friendly"]').click();
  await page.waitForTimeout(700);
  await expect(page.locator('[data-screen="intros"]')).toBeVisible();
  await shot(
    page,
    "Intros · second NPC",
    "Different archetype, different greeting. The IntroPanel rotates through every non-partner Heartbreaker in stable order, sets baseline familiarity 25."
  );

  // ─── 8. INTROS: BANTER PICK ────────────────────────────────
  await page.locator('[data-intent="intro_banter"]').click();
  await expect(page.locator('[data-screen="intros"][data-state="dialogue-complete"]')).toBeVisible({ timeout: 10_000 });
  await page.waitForTimeout(220);
  await shot(
    page,
    "Intros · banter pick",
    "The Banter response. Self-roast, charming. Each chosen dynamic biases the relationship's baseline — the foundation for later interactions."
  );

  // ─── 9. SETTINGS DIALOG ────────────────────────────────────
  await page.getByLabel("Open settings").click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.waitForTimeout(220);
  await shot(
    page,
    "Settings",
    "Configuration drawer. Dark gradient, gold-bordered, custom switch with golden dot. Typewriter speed, reduce motion, audio coming later."
  );
  await page.getByRole("dialog").getByRole("button", { name: "Close" }).click();
  await page.waitForTimeout(200);

  // ─── 10. RIGHT RAIL: FIELD REPORT ──────────────────────────
  // Walk through enough intros that the right rail shows variety. Burn 3 more.
  for (let i = 0; i < 3; i += 1) {
    const choice = page.locator('[data-intent="intro_friendly"]:not([disabled])');
    if ((await choice.count()) === 0) break;
    await choice.click();
    await page.waitForTimeout(600);
  }
  await page.getByLabel("Open right rail").click();
  await page.waitForTimeout(300);
  await shot(
    page,
    "Field Report rail",
    "Right rail open. Where everyone is, current couples (player-couple highlighted gold), the cast grid, and a memories scroll — the field report between scenes."
  );

  // ─── 11. CAST POPOUT: WHAT YOU KNOW ────────────────────────
  await page.getByRole("button", { name: /Open .* profile/ }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.waitForTimeout(500);
  await shot(
    page,
    "Cast popout · discovery",
    "Heartbreaker profile. Backstory, relationship bars, Ideal-Match (gated by familiarity), and 'What you know' — the structured trait knowledge revealed through conversation."
  );
  await page.getByRole("dialog").getByRole("button", { name: "Close" }).first().click();
  await page.waitForTimeout(180);

  // ─── 12. FINISH INTROS, REACH MAIN STAGE ───────────────────
  // Click through any remaining intros + ceremonies until we're back to normal turns.
  for (let step = 0; step < 25; step += 1) {
    if (await page.locator('[data-screen="ceremony"]').count()) {
      await page.getByRole("button", { name: "Continue" }).click({ force: true });
      await page.waitForTimeout(220);
      continue;
    }
    if (await page.locator('[data-screen="day-recap"]').count()) {
      await page.locator('[data-screen="day-recap"]').getByRole("button", { name: "Continue" }).click();
      await page.waitForTimeout(220);
      continue;
    }
    const intro = page.locator('[data-intent="intro_friendly"]:not([disabled])');
    if ((await intro.count()) > 0) {
      await intro.click();
      await page.waitForTimeout(400);
      continue;
    }
    break;
  }
  // We should now be on the main scene-dialogue stage.
  await expect(page.getByTestId("choice-fan")).toBeVisible();
  await page.waitForTimeout(220);
  await shot(
    page,
    "Main stage",
    "Sunset Bay, afternoon. The player remains visible while response bubbles fan out from the bottom of the scene."
  );

  // ─── 13. CONVERSATION IN PROGRESS ──────────────────────────
  // Click first available choice (likely a Spark with the partner).
  const firstChoice = page.locator('[data-testid="choice"]:not([disabled])').first();
  await firstChoice.click();
  await page.waitForSelector('[data-testid="choice-fan"], [data-screen="ceremony"]', { timeout: 15_000 });
  await page.waitForTimeout(280);
  if (await page.locator('[data-screen="ceremony"]').count() === 0) {
    await shot(
      page,
      "Conversation",
      "A real chat. Player bubble (accent orange, right-aligned), NPC bubble (cream, gold-gradient outline), audience delta + intent chip on the outcome row."
    );
  }

  // ─── 14. ADVANCE THROUGH MULTIPLE TURNS HUNTING FOR EVENTS ─
  let recapCaptured = false;
  let throbCaptured = false;
  let flushCaptured = false;
  let pairingCaptured = false;

  const loopStart = Date.now();
  for (let turn = 0; turn < 220; turn += 1) {
    if (page.url().includes("/finale")) break;
    if (Date.now() - loopStart > 200_000) break; // hard wall after ~3.3 minutes

    if (await page.locator('[data-screen="day-recap"]').count()) {
      if (!recapCaptured) {
        await page.waitForTimeout(300);
        await shot(
          page,
          "Day boundary recap",
          "End-of-day modal. Recap of what happened while you were busy, plus the Pulse Board (audience standings). Gold ampersands between couples."
        );
        recapCaptured = true;
      }
      await page.locator('[data-screen="day-recap"]').getByRole("button", { name: "Continue" }).click({ force: true });
      await page.waitForTimeout(180);
      continue;
    }
    if (await page.locator('[data-screen="ceremony"]').count()) {
      const text = (await page.locator('[data-screen="ceremony"]').textContent({ timeout: 4_000 })) ?? "";
      if (/Heart Throb/i.test(text) && !throbCaptured) {
        await page.waitForTimeout(400);
        await shot(
          page,
          "Heart Throb arrives",
          "A new Heart Throb walks into Sunset Bay. Cinematic overlay, gold lighting, larger portrait fade-in — state-conditioned by the Producer to disrupt a specific connection."
        );
        throbCaptured = true;
      } else if (/Flush of Hearts/i.test(text) && !flushCaptured) {
        await page.waitForTimeout(400);
        await shot(
          page,
          "Flush of Hearts",
          "The mid-show twist. Multiple new arrivals at once, testing the existing couples. Pairs ceremony reveal with staggered animation."
        );
        flushCaptured = true;
      } else if (/Pairing Ceremony/i.test(text) && !pairingCaptured) {
        await page.waitForTimeout(400);
        await shot(
          page,
          "Pairing Ceremony",
          "A regular re-coupling. The cast lines up; couples are locked. Notice the gold-bordered pair rows animate in one by one."
        );
        pairingCaptured = true;
      }
      await page.getByRole("button", { name: "Continue" }).click({ force: true, timeout: 5_000 }).catch(() => undefined);
      await page.waitForTimeout(220);
      continue;
    }
    const buttons = page.locator('[data-testid="choice"]:not([disabled])');
    const count = await buttons.count();
    if (count === 0) break;
    let pick = 0;
    for (let i = 0; i < count; i += 1) {
      const text = (await buttons.nth(i).innerText()).toLowerCase();
      if (/chat|deep|share|listen|comfort|pair|propose|private_suite/.test(text)) { pick = i; break; }
    }
    await buttons.nth(pick).click({ force: true, timeout: 5_000 }).catch(() => undefined);
    try {
      await page.waitForSelector('[data-testid="choice-fan"], [data-screen="ceremony"], [data-screen="day-recap"], [data-screen="finale"]', { timeout: 8_000 });
    } catch { /* loop will handle */ }
    if (turn > 0 && turn % 40 === 0) {
      // Defensive break if the loop is spinning without progress (e.g. stuck dialog).
      const stuck = await page.locator('[data-state="dialogue-streaming"]').count();
      if (stuck > 0) {
        await page.waitForTimeout(500);
      }
    }
  }

  // ─── 15. FINALE ────────────────────────────────────────────
  const finaleHeading = page.getByRole("heading", { name: /crowns its couple/i });
  try {
    await expect(finaleHeading).toBeVisible({ timeout: 20_000 });
    await page.waitForTimeout(450);
    await shot(
      page,
      "Finale",
      "Sunset Bay crowns its couple. Gold palette, the winning couple front and center, couple-strength, outcome, Heart Beats earned. The end of the run."
    );
  } catch {
    // Even without reaching finale, the gallery is still valuable.
    // The afterEach hook writes it. Test still passes if we've got the core beats.
  }

  // Beat coverage check — must reach a meaningful slice of the showcase.
  expect(beats.length).toBeGreaterThanOrEqual(13);
  for (const required of ["Title", "First Spark", "Intros"]) {
    expect(beats.some((b) => b.title.toLowerCase().includes(required.toLowerCase()))).toBeTruthy();
  }
});

function renderGallery(items: Beat[]): string {
  const slides = items
    .map(
      (b) => `
    <article class="slide" id="slide-${b.index}">
      <header>
        <span class="slide-num">${String(b.index).padStart(2, "0")}</span>
        <h2>${escapeHtml(b.title)}</h2>
      </header>
      <figure>
        <img src="${b.file}" alt="${escapeHtml(b.title)}" />
      </figure>
      <p class="caption">${escapeHtml(b.caption)}</p>
    </article>`,
    )
    .join("\n");

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Paradise Hearts · Golden Playthrough</title>
  <style>
    :root {
      --bg-deep: #070504;
      --bg: #0d0a08;
      --ink: #faf6ef;
      --muted: #b5a187;
      --gold: #d9a73a;
      --gold-soft: #f4e3b8;
      --accent: #d4633e;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background:
        radial-gradient(80% 60% at 50% -10%, rgba(212,99,62,.22), transparent 50%),
        var(--bg-deep);
      color: var(--ink);
      font-family: -apple-system, "Segoe UI", system-ui, sans-serif;
      min-height: 100vh;
      padding: 6vh 4vw 12vh;
    }
    header.banner {
      text-align: center;
      max-width: 880px;
      margin: 0 auto 6vh;
    }
    .eyebrow {
      font-style: italic;
      color: var(--gold-soft);
      letter-spacing: .14em;
      text-transform: uppercase;
      font-size: 13px;
    }
    h1 {
      margin-top: 12px;
      font-family: "Iowan Old Style", Charter, Georgia, serif;
      font-size: clamp(48px, 7vw, 96px);
      font-weight: 700;
      letter-spacing: -.02em;
      line-height: 1;
    }
    h1 .italic {
      font-style: italic;
      background: linear-gradient(110deg, #a87a1f 25%, #f4e3b8 50%, #a87a1f 75%);
      background-size: 220% 100%;
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }
    .tagline {
      margin-top: 16px;
      font-style: italic;
      color: var(--muted);
      font-size: 16px;
    }
    .stats {
      margin-top: 22px;
      font-size: 12px;
      letter-spacing: .12em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .deck {
      max-width: 1280px;
      margin: 0 auto;
      display: grid;
      gap: 60px;
    }
    .slide {
      display: grid;
      gap: 18px;
      padding: 24px;
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(20,16,12,.65), rgba(8,6,4,.85));
      border: 1px solid rgba(217,167,58,.25);
      box-shadow: 0 18px 60px rgba(0,0,0,.45), inset 0 1px 0 rgba(248,236,210,.06);
    }
    .slide header {
      display: flex;
      align-items: baseline;
      gap: 14px;
      border-bottom: 1px solid rgba(217,167,58,.18);
      padding-bottom: 12px;
    }
    .slide-num {
      font-family: "Iowan Old Style", Charter, Georgia, serif;
      font-size: 36px;
      font-weight: 700;
      color: var(--gold);
      letter-spacing: -.04em;
      font-variant-numeric: tabular-nums;
    }
    .slide h2 {
      font-family: "Iowan Old Style", Charter, Georgia, serif;
      font-size: 26px;
      font-style: italic;
      color: var(--ink);
      letter-spacing: -.01em;
    }
    .slide figure {
      position: relative;
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid rgba(217,167,58,.28);
      background: var(--bg);
    }
    .slide img {
      display: block;
      width: 100%;
      height: auto;
    }
    .caption {
      font-size: 15px;
      line-height: 1.55;
      color: var(--muted);
      max-width: 76ch;
    }

    nav.toc {
      position: fixed;
      right: 24px; top: 50%;
      transform: translateY(-50%);
      display: flex;
      flex-direction: column;
      gap: 8px;
      z-index: 10;
    }
    nav.toc a {
      display: block;
      width: 10px; height: 10px;
      border-radius: 50%;
      background: rgba(248,236,210,.18);
      transition: background .2s, transform .2s;
    }
    nav.toc a:hover { background: var(--gold); transform: scale(1.4); }

    @media (max-width: 720px) {
      nav.toc { display: none; }
      body { padding: 4vh 3vw 8vh; }
      .deck { gap: 36px; }
      .slide { padding: 16px; }
    }
  </style>
</head>
<body>
  <header class="banner">
    <p class="eyebrow">A Paradise Hearts production</p>
    <h1>Paradise <span class="italic">Hearts</span></h1>
    <p class="tagline">Golden Playthrough — the sizzle reel.</p>
    <p class="stats">${items.length} beats · captured ${new Date().toISOString().slice(0, 10)} · 1600 × 900</p>
  </header>

  <nav class="toc" aria-label="Beat navigation">
    ${items.map((b) => `<a href="#slide-${b.index}" title="${escapeHtml(b.title)}"></a>`).join("")}
  </nav>

  <div class="deck">${slides}</div>
</body>
</html>
`;
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!),
  );
}
