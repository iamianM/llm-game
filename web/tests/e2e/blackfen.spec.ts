import { expect, test } from "@playwright/test";

test("Blackfen starts and accepts freeform input", async ({ page }) => {
  await page.goto("/blackfen");
  await expect(page.getByRole("heading", { name: "Blackfen Road" })).toBeVisible();
  await page.getByRole("button", { name: "Start Run" }).click();
  await expect(page).toHaveURL(/\/blackfen\/play\//);
  await expect(page.getByRole("heading", { name: "Blackfen Village" })).toBeVisible();
  await page.getByPlaceholder("What do you do?").fill("talk to Mara Vell");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("You speak with Mara Vell.")).toBeVisible();
});
