import { expect, test } from "@playwright/test";

test("starts a run from character creation", async ({ page }) => {
  await page.goto("/new-run");
  await expect(page.getByText("Heartthrob")).toBeVisible();
  await page.getByRole("button", { name: "Step into Sunset Bay" }).click();
  await expect(page).toHaveURL(/\/play\/.+/);
  await expect(page.locator('[data-screen="stage"]')).toBeVisible();
});

test("mobile casting carousel fits the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 740 });
  await page.goto("/new-run");
  await expect(page.getByTestId("archetype-carousel")).toBeVisible();

  const metrics = await page.evaluate(() => {
    const carousel = document.querySelector('[data-testid="archetype-carousel"]');
    const selectedCard = document.querySelector('.archetype-card[aria-pressed="true"]');
    const carouselBox = carousel?.getBoundingClientRect();
    const cardBox = selectedCard?.getBoundingClientRect();
    return {
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
      documentOverflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      bodyOverflowX: document.body.scrollWidth - document.body.clientWidth,
      bodyOverflowY: document.body.scrollHeight - document.body.clientHeight,
      carouselLeft: carouselBox?.left ?? -1,
      carouselRight: carouselBox?.right ?? -1,
      cardLeft: cardBox?.left ?? -1,
      cardRight: cardBox?.right ?? -1,
      cardHeight: cardBox?.height ?? 0
    };
  });

  expect(metrics.documentOverflowX).toBeLessThanOrEqual(1);
  expect(metrics.bodyOverflowX).toBeLessThanOrEqual(1);
  expect(metrics.bodyOverflowY).toBeLessThanOrEqual(1);
  expect(metrics.carouselLeft).toBeGreaterThanOrEqual(0);
  expect(metrics.carouselRight).toBeLessThanOrEqual(metrics.viewportWidth);
  expect(metrics.cardLeft).toBeGreaterThanOrEqual(0);
  expect(metrics.cardRight).toBeLessThanOrEqual(metrics.viewportWidth);
  expect(metrics.cardHeight).toBeGreaterThan(320);

  await page.getByRole("button", { name: "Next archetype" }).click();
  await expect(page.getByRole("tab", { name: "Class Clown" })).toHaveAttribute("aria-selected", "true");
});

test("mobile can open checkpoints from casting", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 740 });
  await page.goto("/new-run");

  await page.getByRole("button", { name: "Checkpoints" }).click();

  const dialog = page.getByRole("dialog", { name: "Resume from checkpoint" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Choose a checkpoint" })).toBeVisible();
  await expect(dialog.locator(".checkpoint-card").first()).toBeVisible();
});
