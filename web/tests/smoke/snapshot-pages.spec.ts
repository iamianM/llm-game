import { expect, test } from "@playwright/test";
import path from "node:path";

const out = (name: string) => path.join(process.cwd(), "tests", "snapshots", name);

test("captures primary screen snapshots", async ({ page }) => {
  test.setTimeout(140_000);
  await page.goto("/");
  await page.screenshot({ path: out("title.png"), fullPage: true });

  await page.getByRole("link", { name: "New Run" }).click();
  await page.screenshot({ path: out("new-run.png"), fullPage: true });

  await page.getByRole("button", { name: "Test mode" }).click();
  await page.getByRole("button", { name: "Step into Sunset Bay" }).click();
  await expect(page.locator('[data-screen="stage"]')).toBeVisible();
  await page.waitForSelector('[data-testid="choice-fan"]', { timeout: 15_000 });
  await page.screenshot({ path: out("stage-start.png"), fullPage: true });

  await page.getByLabel("Open right rail").click();
  await expect(page.getByText("Where everyone is")).toBeVisible();
  await page.waitForTimeout(350);
  await page.screenshot({ path: out("rail-open.png"), fullPage: true });
  await page.getByRole("button", { name: "Open Chloe profile" }).click();
  await page.screenshot({ path: out("cast-popout.png"), fullPage: true });
  await page.getByRole("dialog").getByRole("button", { name: "Close" }).first().click();

  await page.getByLabel("Open settings").click();
  await page.screenshot({ path: out("settings.png"), fullPage: true });
  await page.getByRole("dialog").getByRole("button", { name: "Close" }).first().click();

  await page.getByRole("button", { name: "Pair with Chloe" }).click();
  await expect(page.locator('[data-screen="ceremony"]')).toBeVisible();
  await page.screenshot({ path: out("ceremony-first-spark.png"), fullPage: true });
  await page.getByRole("button", { name: "Continue" }).click();
  await page.screenshot({ path: out("play-day1-intros.png"), fullPage: true });

  await page.getByTestId("choice-menu").getByRole("button").first().click();
  await page.waitForSelector('[data-state="dialogue-complete"]', { timeout: 15_000 });
  await page.screenshot({ path: out("play-day1-conversation.png"), fullPage: true });

  for (let turn = 0; turn < 20; turn += 1) {
    if (await page.getByText("Lounge", { exact: false }).count()) break;
    if (await page.locator('[data-screen="day-recap"]').count()) {
      await page.screenshot({ path: out("day-recap.png"), fullPage: true });
      await page.locator('[data-screen="day-recap"]').getByRole("button", { name: "Continue" }).click();
      continue;
    }
    if (await page.locator('[data-screen="ceremony"]').count()) {
      await page.getByRole("button", { name: "Continue" }).click();
      continue;
    }
    const choices = page.locator('[data-testid="choice"]:not([disabled])');
    if ((await choices.count()) === 0) break;
    await choices.first().click();
    await advanceScene(page);
  }
  await page.screenshot({ path: out("play-day1-ambient.png"), fullPage: true });
});

async function advanceScene(page: import("@playwright/test").Page) {
  for (let step = 0; step < 8; step += 1) {
    await page.waitForTimeout(160);
    if (await page.locator('[data-testid="choice-fan"], [data-screen="ceremony"], [data-screen="day-recap"], [data-screen="finale"]').count()) return;
    if (await page.locator('[data-testid="player-bubble"], [data-testid="speech-bubble"], [data-testid="narrator-bubble"]').count()) {
      await page.getByTestId("scene-stage").click({ force: true });
      continue;
    }
    return;
  }
}
