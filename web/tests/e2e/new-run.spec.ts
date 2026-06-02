import { expect, test } from "@playwright/test";

test("starts a run from character creation", async ({ page }) => {
  await page.goto("/new-run");
  await expect(page.getByRole("heading", { name: "Choose your Heartbreaker" })).toBeVisible();
  await page.getByRole("button", { name: /^Play as / }).click();
  await expect(page).toHaveURL(/\/play\/.+/);
  await expect(page.locator('[data-screen="stage"]')).toBeVisible();
});

test("mobile casting roster fits the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 740 });
  await page.goto("/new-run");
  await expect(page.getByTestId("roster-grid")).toBeVisible();

  const metrics = await page.evaluate(() => {
    const roster = document.querySelector('[data-testid="roster-grid"]');
    const selectedCard = document.querySelector('.roster-card[aria-checked="true"]');
    const rosterBox = roster?.getBoundingClientRect();
    const cardBox = selectedCard?.getBoundingClientRect();
    return {
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
      documentOverflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      bodyOverflowX: document.body.scrollWidth - document.body.clientWidth,
      rosterLeft: rosterBox?.left ?? -1,
      rosterRight: rosterBox?.right ?? -1,
      cardLeft: cardBox?.left ?? -1,
      cardRight: cardBox?.right ?? -1,
      cardHeight: cardBox?.height ?? 0
    };
  });

  expect(metrics.documentOverflowX).toBeLessThanOrEqual(1);
  expect(metrics.bodyOverflowX).toBeLessThanOrEqual(1);
  expect(metrics.rosterLeft).toBeGreaterThanOrEqual(0);
  expect(metrics.rosterRight).toBeLessThanOrEqual(metrics.viewportWidth);
  expect(metrics.cardLeft).toBeGreaterThanOrEqual(0);
  expect(metrics.cardRight).toBeLessThanOrEqual(metrics.viewportWidth);
  expect(metrics.cardHeight).toBeGreaterThan(80);

  await page.getByRole("radio", { name: /Deon/ }).click();
  await expect(page.getByRole("radio", { name: /Deon/ })).toHaveAttribute("aria-checked", "true");
});

test("mobile can open checkpoints from casting", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 740 });
  await page.goto("/new-run");

  await page.getByRole("button", { name: "Resume from checkpoint" }).click();

  const dialog = page.getByRole("dialog", { name: "Resume from checkpoint" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Choose a checkpoint" })).toBeVisible();
  await expect(dialog.locator(".checkpoint-card").first()).toBeVisible();
});
