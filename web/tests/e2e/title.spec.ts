import { expect, test } from "@playwright/test";

test("title screen routes to new run", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Paradise Hearts" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Continue Run" })).toBeDisabled();
  await page.getByRole("link", { name: "New Run" }).click();
  await expect(page).toHaveURL(/\/new-run$/);
});
