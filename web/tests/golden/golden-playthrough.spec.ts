/**
 * Golden Playthrough — the curated showcase walk-through.
 *
 * Unlike `e2e/full-playthrough.spec.ts` (which proves the engine survives a
 * randomized 6-day run), this spec is a deterministic, hand-choreographed tour
 * of the primary opening-loop UI in Paradise Hearts. It captures wide-format
 * portfolio screenshots and assembles them into a slideshow gallery. Later-run
 * event coverage belongs to the full playthrough and focused contract specs.
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
  test.setTimeout(180_000);
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await page.setViewportSize({ width: 1600, height: 900 });
  fs.mkdirSync(SHOTS_DIR, { recursive: true });
  // The gallery is a generated artifact. Remove images from the previous
  // choreography so renamed or deleted beats cannot masquerade as current UI.
  for (const file of fs.readdirSync(SHOTS_DIR)) {
    if (file.endsWith(".png") || file === "index.html") {
      fs.rmSync(path.join(SHOTS_DIR, file));
    }
  }
  beats.length = 0;
  beatIndex = 0;

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
  // The current game opens with the Day-1 round-robin introductions inside
  // the cinematic scene system. Dialogue beats precede each choice fan.
  await expect(page.getByTestId("scene-stage")).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('[data-testid="speech-bubble"], [data-testid="narrator-bubble"]').first()).toBeVisible();
  // Speed up animations + typewriter for the rest of the showcase.
  await page.getByLabel("Open settings").click();
  await page.getByLabel("Typewriter speed").selectOption("instant");
  await page.getByLabel("Reduce motion").check();
  await page.getByRole("dialog").getByRole("button", { name: "Close" }).click();
  await page.waitForTimeout(200);

  // ─── 4. INTROS: FIRST NPC GREETS ───────────────────────────
  await shot(
    page,
    "Intros · first greeting",
    "Day-1 introductions play through the same cinematic scene system used by ordinary conversations and event narration."
  );

  // ─── 5. INTROS: RESPONSE OPTIONS ───────────────────────────
  await advanceToChoiceFan(page);
  await expect(page.getByRole("button", { name: /Get deep with/ })).toBeVisible();
  await shot(
    page,
    "Intros · response options",
    "The player gets four fully written responses — Friendly, Flirty, Deep, and Banter — from the engine's shared legal-action surface."
  );

  // ─── 6. INTROS: RESPONSE LANDS ─────────────────────────────
  await page.getByRole("button", { name: /Get deep with/ }).click();
  await expect(page.locator('[data-testid="player-bubble"], [data-testid="speech-bubble"]').first()).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("scene-stage").click({ force: true });
  await page.waitForTimeout(180);
  await shot(
    page,
    "Intros · deep response lands",
    "The chosen Deep response and NPC reply are replayable scene beats backed by the recorded turn result."
  );

  // ─── 7. SETTINGS DIALOG ────────────────────────────────────
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

  // ─── 8. FINISH INTROS, REACH FIRST SPARK ───────────────────
  for (let step = 0; step < 120; step += 1) {
    const pairChoice = page.getByRole("button", { name: /^Pair with / });
    if (await pairChoice.count()) break;
    const intro = page.locator('button[aria-label^="Be friendly with"]:not([disabled])');
    if (await intro.count()) {
      await intro.first().click({ force: true });
    } else if (await page.locator('[data-testid="player-bubble"], [data-testid="speech-bubble"], [data-testid="narrator-bubble"]').count()) {
      await page.getByTestId("scene-stage").click({ force: true });
    }
    await page.waitForTimeout(140);
  }
  const openingPairChoice = page.getByRole("button", { name: /^Pair with / }).first();
  await expect(openingPairChoice).toBeVisible({ timeout: 15_000 });
  await shot(
    page,
    "First Spark choices",
    "The first coupling decision appears only after the player has met the cast. The engine exposes the legal partners; the browser renders the shared action vocabulary."
  );

  // ─── 9. FIRST SPARK CEREMONY ───────────────────────────────
  await openingPairChoice.click();
  await expect(page.locator('[data-screen="ceremony"]')).toBeVisible({ timeout: 15_000 });
  await page.waitForTimeout(300);
  await shot(
    page,
    "First Spark ceremony",
    "Paradise Calls · First Spark. The deterministic coupling resolves before the narrator presents the ceremony beat."
  );
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.locator('[data-testid="narrator-bubble"], [data-testid="speech-bubble"]').first()).toBeVisible({ timeout: 15_000 });
  await shot(
    page,
    "Challenge reveal",
    "The post-coupling Compatibility Quiz arrives as a narrated scene beat, while scoring remains deterministic engine state."
  );
  await advanceToChoiceFan(page);
  await shot(
    page,
    "Compatibility Quiz choices",
    "A round-based minigame uses the same typed action and scene pipeline as conversations, ceremonies, replay, and eval scenarios."
  );

  // ─── 10. RIGHT RAIL: FIELD REPORT ──────────────────────────
  if (await page.getByLabel("Open right rail").count()) await page.getByLabel("Open right rail").click();
  await page.waitForTimeout(220);
  await shot(
    page,
    "Field Report rail",
    "The live field report combines resort locations, current couples, cast profiles, and remembered facts without moving canonical state into the browser."
  );

  // ─── 11. CAST POPOUT: WHAT YOU KNOW ────────────────────────
  await page.getByRole("button", { name: /Open .* profile/ }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.waitForTimeout(250);
  await shot(
    page,
    "Cast popout · discovery",
    "A Heartbreaker profile combines relationship signals with gated, structured knowledge learned through play."
  );
  await page.getByRole("dialog").getByRole("button", { name: "Close" }).first().click();
  if (await page.getByLabel("Close right rail").count()) {
    await page.getByLabel("Close right rail").evaluate((button: HTMLButtonElement) => button.click());
  }

  // Beat coverage check — must reach a meaningful slice of the showcase.
  expect(beats.length).toBeGreaterThanOrEqual(11);
  for (const required of ["Title", "First Spark", "Intros", "Challenge"]) {
    expect(beats.some((b) => b.title.toLowerCase().includes(required.toLowerCase()))).toBeTruthy();
  }
  expect(consoleErrors).toEqual([]);
});

async function advanceToChoiceFan(page: import("@playwright/test").Page) {
  for (let step = 0; step < 20; step += 1) {
    if (await page.getByTestId("choice-fan").count()) return;
    await page.getByTestId("scene-stage").click({ force: true });
    await page.waitForTimeout(120);
  }
  await expect(page.getByTestId("choice-fan")).toBeVisible();
}

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
