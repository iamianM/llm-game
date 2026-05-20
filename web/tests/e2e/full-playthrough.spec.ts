import { expect, test } from "@playwright/test";
import path from "node:path";

const out = (name: string) => path.join(process.cwd(), "tests", "snapshots", name);

test("complete mock playthrough reaches finale", async ({ page }) => {
  test.setTimeout(720_000);
  await page.goto("/");
  await page.getByRole("link", { name: "New Run" }).click();
  await page.getByRole("button", { name: "Test mode" }).click();
  await page.getByRole("button", { name: "Step into Sunset Bay" }).click();
  await expect(page.getByTestId("choice-menu")).toBeVisible();
  // Speed up dialogue + animations so the long playthrough fits in budget.
  await page.getByLabel("Open settings").click();
  await page.getByLabel("Typewriter speed").selectOption("instant");
  await page.getByLabel("Reduce motion").check();
  await page.getByRole("dialog").getByRole("button", { name: "Close" }).click();
  let sawDayRecap = false;
  let sawFirstSpark = false;
  let sawPairingCeremony = false;
  let sawFlushOfHearts = false;

  for (let turn = 0; turn < 420; turn += 1) {
    if (page.url().includes("/finale") || await page.getByRole("heading", { name: "Sunset Bay crowns its couple" }).count()) break;
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
      await page.waitForSelector('[data-testid="choice"]:not([disabled])', { timeout: 15_000 });
    } catch {
      break;
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
    await page.waitForSelector('[data-state="dialogue-complete"], [data-screen="ceremony"], [data-screen="finale"]', { timeout: 15_000 });
    if (page.url().includes("/finale") || await page.getByRole("heading", { name: "Sunset Bay crowns its couple" }).count()) break;
  }

  await expect(page.getByRole("heading", { name: "Sunset Bay crowns its couple" })).toBeVisible({ timeout: 10_000 });
  await page.screenshot({ path: out("finale.png"), fullPage: true });
  await expect(page.getByText("Heart Beats")).toBeVisible();
  expect(sawFirstSpark).toBeTruthy();
  expect(sawPairingCeremony).toBeTruthy();
  expect(sawFlushOfHearts).toBeTruthy();
  expect(sawDayRecap).toBeTruthy();
});
