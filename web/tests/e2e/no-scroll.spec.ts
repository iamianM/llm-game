import { expect, test } from "@playwright/test";

/**
 * Games don't scroll. Each main route must fit the viewport.
 * Modals/popouts (role=dialog) can scroll internally; the body cannot.
 */

async function bodyScroll(page: import("@playwright/test").Page) {
  return page.evaluate(() => ({
    docScroll: document.documentElement.scrollHeight - document.documentElement.clientHeight,
    bodyScroll: document.body.scrollHeight - document.body.clientHeight,
    overflowY: window.getComputedStyle(document.body).overflowY
  }));
}

test("title fits viewport without scroll", async ({ page }) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  const m = await bodyScroll(page);
  expect(m.overflowY).toBe("hidden");
  expect(m.bodyScroll).toBeLessThanOrEqual(1);
});

test("new-run fits viewport without scroll", async ({ page }) => {
  await page.goto("/new-run");
  await page.waitForLoadState("networkidle");
  const m = await bodyScroll(page);
  expect(m.overflowY).toBe("hidden");
  expect(m.bodyScroll).toBeLessThanOrEqual(1);
});

test("stage fits viewport without scroll", async ({ page }) => {
  await page.goto("/new-run");
  await page.getByRole("button", { name: "Step into Sunset Bay" }).click();
  await expect(page.getByTestId("choice-fan").or(page.getByText("Day-1 Introductions"))).toBeVisible();
  const m = await bodyScroll(page);
  expect(m.overflowY).toBe("hidden");
  expect(m.bodyScroll).toBeLessThanOrEqual(1);
});
