import { expect, test } from "@playwright/test";

test("starts a run from character creation", async ({ page }) => {
  await page.goto("/new-run");
  await expect(page.getByText("Heartthrob")).toBeVisible();
  await expect(page.getByText("Class Clown")).toBeVisible();
  await expect(page.getByText("Loyal Friend")).toBeVisible();
  await expect(page.getByRole("button", { name: "Test mode" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Real mode" })).toBeVisible();
  await page.getByRole("button", { name: "Test mode" }).click();
  await page.getByRole("button", { name: "Step into Sunset Bay" }).click();
  await expect(page).toHaveURL(/\/play\/.+/);
  await expect(page.locator('[data-screen="stage"]')).toBeVisible();
});
