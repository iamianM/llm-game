import { expect, test } from "@playwright/test";
import path from "node:path";

const out = (name: string) => path.join(process.cwd(), "tests", "snapshots", name);

test("complete mock playthrough reaches finale", async ({ page }) => {
  test.setTimeout(720_000);
  await page.goto("/");
  await page.getByRole("link", { name: "New Run" }).click();
  await page.getByRole("button", { name: "Step into Sunset Bay" }).click();
  // The play screen opens on the Day-1 intro round-robin: NPCs greet you one at
  // a time as dialogue bubbles, and the first choice fan only appears once those
  // greetings have been advanced through. Wait for the stage, speed everything
  // up, then click past the intros before asserting the first interactive fan.
  await page.waitForSelector('[data-testid="scene-stage"]', { timeout: 30_000 });
  // Speed up dialogue + animations so the long playthrough fits in budget.
  await page.getByLabel("Open settings").click();
  await page.getByLabel("Typewriter speed").selectOption("instant");
  await page.getByLabel("Reduce motion").check();
  await page.getByRole("dialog").getByRole("button", { name: "Close" }).click();
  await advanceToChoices(page);
  await expect(page.locator('[data-testid="choice"], [data-testid="choice-fan"]').first()).toBeVisible();
  let sawDayRecap = false;
  let sawFirstSpark = false;
  let sawPairingCeremony = false;
  let sawFlushOfHearts = false;

  for (let turn = 0; turn < 420; turn += 1) {
    if (page.url().includes("/finale") || await page.locator('[data-screen="finale"]').count()) break;
    await advanceScene(page);
    if (page.url().includes("/finale") || await page.locator('[data-screen="finale"]').count()) break;
    if (await page.locator('[data-screen="day-recap"]').count()) {
      sawDayRecap = true;
      await page.screenshot({ path: out("day-recap.png"), fullPage: true });
      await page.locator('[data-screen="day-recap"]').getByRole("button", { name: "Continue" }).click({ force: true });
      continue;
    }
    if (await page.locator('[data-screen="ceremony"]').count()) {
      const ceremonyText = await page.locator('[data-screen="ceremony"]').textContent({ timeout: 5_000 }) ?? "";
      if (/First Spark/i.test(ceremonyText)) sawFirstSpark = true;
      if (/Pairing Ceremony/i.test(ceremonyText)) sawPairingCeremony = true;
      if (/Flush of Hearts/i.test(ceremonyText)) sawFlushOfHearts = true;
      if (/Heart Throb/i.test(ceremonyText)) await page.screenshot({ path: out("ceremony-heart-throb.png"), fullPage: true });
      if (/Flush of Hearts/i.test(ceremonyText)) await page.screenshot({ path: out("ceremony-flush-of-hearts.png"), fullPage: true });
      if (/Heart Swap Proposal/i.test(ceremonyText)) await page.screenshot({ path: out("recouple-proposal.png"), fullPage: true });
      if (/Pairing Ceremony/i.test(ceremonyText)) await page.screenshot({ path: out("ceremony-pairing.png"), fullPage: true });
      await expect(page.getByRole("button", { name: "Continue" })).toBeVisible();
      await page.getByRole("button", { name: "Continue" }).click();
      continue;
    }
    const introContinue = page.getByTestId("intro-continue");
    if (await introContinue.count() > 0) {
      await introContinue.click();
      continue;
    }
    try {
      await page.waitForSelector(
        '[data-testid="choice"]:not([disabled]), [data-testid="player-bubble"], [data-testid="speech-bubble"], [data-testid="narrator-bubble"]',
        { timeout: 15_000 },
      );
    } catch {
      break;
    }
    if (await page.locator('[data-testid="player-bubble"], [data-testid="speech-bubble"], [data-testid="narrator-bubble"]').count()) {
      await advanceScene(page);
      continue;
    }
    const introChoice = page.locator('[data-intent="intro_friendly"]:not([disabled])');
    if (await introChoice.count() > 0) {
      await introChoice.click();
    } else {
      const buttons = page.locator('[data-testid="choice"]:not([disabled])');
      await expect(buttons.first()).toBeVisible();
      // Click first available action; engine surfaces something meaningful every turn.
      await buttons.first().click();
    }
    await advanceScene(page);
    if (page.url().includes("/finale") || await page.locator('[data-screen="finale"]').count()) break;
  }

  await expect(page.locator('[data-screen="finale"]')).toBeVisible({ timeout: 10_000 });
  await expect(page.getByRole("heading")).toContainText(/Sunset Bay|final|summer|winners/i);
  await page.screenshot({ path: out("finale.png"), fullPage: true });
  await expect(page.getByText(/Final result:/)).toBeVisible();
  expect(sawFirstSpark).toBeTruthy();
  expect(sawPairingCeremony).toBeTruthy();
  expect(sawFlushOfHearts).toBeTruthy();
  expect(sawDayRecap).toBeTruthy();
});

// Advance past the opening intro round-robin until the first interactive choice
// fan appears (or a ceremony/recap takes over). The intros render as dialogue
// bubbles that advance on a stage click or a dedicated intro-continue button.
async function advanceToChoices(page: import("@playwright/test").Page) {
  for (let step = 0; step < 60; step += 1) {
    if (await page.locator('[data-testid="choice-fan"], [data-testid="choice"]:not([disabled]), [data-screen="ceremony"], [data-screen="day-recap"], [data-screen="finale"]').count()) {
      return;
    }
    const introContinue = page.getByTestId("intro-continue");
    if (await introContinue.count()) {
      await introContinue.first().click({ force: true }).catch(() => {});
    } else {
      await page.getByTestId("scene-stage").click({ force: true }).catch(() => {});
    }
    await page.waitForTimeout(200);
  }
}

async function advanceScene(page: import("@playwright/test").Page) {
  for (let step = 0; step < 8; step += 1) {
    await page.waitForTimeout(180);
    if (page.url().includes("/finale")) return;
    if (await page.locator('[data-testid="choice-fan"], [data-screen="ceremony"], [data-screen="day-recap"], [data-screen="finale"]').count()) return;
    if (await page.locator('[data-testid="player-bubble"], [data-testid="speech-bubble"], [data-testid="narrator-bubble"]').count()) {
      await page.getByTestId("scene-stage").click({ force: true });
      continue;
    }
    return;
  }
}
