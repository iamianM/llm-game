import { expect, test } from "@playwright/test";

test("right rail and cast popout render", async ({ page }) => {
  await page.goto("/new-run");
  await page.getByRole("button", { name: "Test mode" }).click();
  await page.getByRole("button", { name: "Step into Sunset Bay" }).click();
  await page.getByRole("button", { name: "Pair with Chloe" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  // Intros now run one NPC at a time; pick the Deep response option.
  await page.locator('[data-intent="intro_deep"]').click();
  await page.getByLabel("Open right rail").click();
  await expect(page.getByText("Where everyone is")).toBeVisible();
  await expect(page.getByText("Couples")).toBeVisible();
  await page.getByRole("button", { name: "Open Maya profile" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("Type on Paper")).toBeVisible();
  await expect(page.getByText("What you know")).toBeVisible();
  await expect(page.getByText("Relationship")).toBeVisible();
  await page.getByRole("dialog").getByRole("button", { name: "Close" }).first().click();
});
