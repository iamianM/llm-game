import { expect, test } from "@playwright/test";

test("right rail and cast popout render", async ({ page }) => {
  await page.goto("/new-run");
  await page.getByRole("button", { name: /^Play as / }).click();
  await expect(page.locator('[data-screen="stage"]')).toBeVisible();
  await page.getByLabel("Open right rail").click();
  await expect(page.getByText("Where everyone is")).toBeVisible();
  await expect(page.getByText("Couples")).toBeVisible();
  await page.getByRole("button", { name: "Open Maya profile" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("Ideal Match")).toBeVisible();
  await expect(page.getByText("What you know")).toBeVisible();
  await expect(page.getByText("Connection")).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: "Close" }).first().click();
});
