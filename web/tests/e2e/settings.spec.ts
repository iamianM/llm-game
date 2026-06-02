import { expect, test } from "@playwright/test";

test("settings update typewriter and reduce motion", async ({ page }) => {
  await page.goto("/new-run");
  await page.getByRole("button", { name: /^Play as / }).click();
  await page.getByLabel("Open settings").click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByLabel("Typewriter speed").selectOption("instant");
  await page.getByLabel("Reduce motion").check();
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await expect(page.locator("html")).toHaveClass(/reduce-motion/);
});
