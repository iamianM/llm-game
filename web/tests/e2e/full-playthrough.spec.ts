import { expect, test } from "@playwright/test";
import path from "node:path";

const out = (name: string) => path.join(process.cwd(), "tests", "snapshots", name);

test("complete mock playthrough reaches finale", async ({ page }) => {
  test.setTimeout(240_000);
  await page.goto("/");
  await page.getByRole("link", { name: "New Run" }).click();
  await page.getByRole("button", { name: "Test mode" }).click();
  await page.getByRole("button", { name: "Enter Sunset Bay" }).click();
  await expect(page.getByTestId("choice-menu")).toBeVisible();
  let sawDayRecap = false;
  let sawFirstSpark = false;
  let sawPairingCeremony = false;
  let sawFlushOfHearts = false;

  for (let turn = 0; turn < 260; turn += 1) {
    if (page.url().includes("/finale") || await page.getByRole("heading", { name: "Sunset Bay crowns its couple" }).count()) break;
    if (await page.locator('[data-screen="day-recap"]').count()) {
      sawDayRecap = true;
      await page.screenshot({ path: out("day-recap.png"), fullPage: true });
      await page.locator('[data-screen="day-recap"]').getByRole("button", { name: "Continue" }).click({ force: true });
      continue;
    }
    if (await page.locator('[data-screen="ceremony"]').count()) {
      const ceremonyText = await page.locator('[data-screen="ceremony"]').innerText();
      if (/First Spark/i.test(ceremonyText)) sawFirstSpark = true;
      if (/Pairing Ceremony/i.test(ceremonyText)) sawPairingCeremony = true;
      if (/Flush of Hearts/i.test(ceremonyText)) sawFlushOfHearts = true;
      if (/Heart Throb/i.test(ceremonyText)) await page.screenshot({ path: out("ceremony-heart-throb.png"), fullPage: true });
      if (/Flush of Hearts/i.test(ceremonyText)) await page.screenshot({ path: out("ceremony-flush-of-hearts.png"), fullPage: true });
      if (/Heart Swap Proposal/i.test(ceremonyText)) await page.screenshot({ path: out("recouple-proposal.png"), fullPage: true });
      if (/Pairing Ceremony/i.test(ceremonyText)) await page.screenshot({ path: out("ceremony-pairing.png"), fullPage: true });
      await page.getByRole("button", { name: "Continue" }).click({ force: true });
      continue;
    }
    const buttons = page.getByTestId("choice-menu").getByRole("button");
    if ((await buttons.count()) === 0) break;
    await expect(buttons.first()).toBeVisible();
    const count = await buttons.count();
    let chosen = 0;
    for (let index = 0; index < count; index += 1) {
      const text = await buttons.nth(index).innerText();
      if (/Challenge|Join gather|Flush of Hearts|Pair with|Spark .* with|ambient|Lounge|People-watch|Walk away|Move/i.test(text)) {
        chosen = index;
        break;
      }
    }
    await buttons.nth(chosen).click();
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
