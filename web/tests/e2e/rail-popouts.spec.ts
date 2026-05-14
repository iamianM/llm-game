import { expect, test } from "@playwright/test";

test("right rail and cast popout render", async ({ page }) => {
  await page.goto("/new-run");
  await page.getByRole("button", { name: "Test mode" }).click();
  await page.getByRole("button", { name: "Enter Sunset Bay" }).click();
  await page.getByLabel("Open right rail").click();
  await expect(page.getByText("Where everyone is")).toBeVisible();
  await expect(page.getByText("Couples")).toBeVisible();
  await page.getByRole("button", { name: "Open Chloe profile" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("Type on Paper")).toBeVisible();
  await page.getByRole("button", { name: "Close" }).last().click();
});
