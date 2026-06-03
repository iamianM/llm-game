import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

test("Blackfen starts and accepts freeform input", async ({ page }) => {
  await page.goto("/blackfen");
  await expect(page.getByRole("heading", { name: "Blackfen Road" })).toBeVisible();
  await page.getByRole("button", { name: "Start Run" }).click();
  await expect(page).toHaveURL(/\/blackfen\/play\//);
  await expect(page.getByRole("heading", { name: "Blackfen Village" })).toBeVisible();
  await submitAction(page, "talk to Mara Vell", 1);
  await expect(page.getByText("You speak with Mara Vell.").first()).toBeVisible();
});

test("Blackfen mobile combat keeps party and threats visible", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/blackfen");
  await page.getByRole("button", { name: "Start Run" }).click();
  await submitAction(page, "go north road", 1);

  await expect(page.getByText("HP 22/22").first()).toBeVisible();
  await expect(page.getByText("Road Bandit A").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Inventory" })).toBeVisible();
});

test("Blackfen explains unclear freeform input", async ({ page }) => {
  await page.goto("/blackfen");
  await page.getByRole("button", { name: "Start Run" }).click();
  await submitAction(page, "dance in the rain", 1);

  await expect(page.getByText("I treated that as looking around for anything useful.")).toBeVisible();
});

test("Blackfen victory path reaches terminal panel", async ({ page }) => {
  await page.goto("/blackfen");
  await page.getByRole("button", { name: "Start Run" }).click();
  const actions = [
    "talk to Mara Vell",
    "go north road",
    "attack",
    "attack",
    "go rusted watchtower",
    "attack",
    "attack",
    "go north road",
    "go hill shrine",
    "rest",
    "inspect shrine",
    "go sunken chapel",
    "inspect chapel",
    "go barrow crypt",
    "attack",
    "attack",
    "attack",
    "attack",
    "inspect crypt"
  ];
  for (const [index, action] of actions.entries()) await submitAction(page, action, index + 1);

  await expect(page.getByText("The Bell Falls Silent")).toBeVisible();
  await expect(page.getByRole("button", { name: "Copy Seed" })).toBeVisible();
  await expect(page.getByPlaceholder("This run is over.")).toBeDisabled();
});

async function submitAction(page: Page, action: string, turnIndex: number) {
  const input = page.getByPlaceholder("What do you do?");
  await input.fill(action);
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(`#${turnIndex} ${action}`).first()).toBeAttached();
  if ((await page.getByPlaceholder("What do you do?").count()) > 0) await expect(input).toHaveValue("");
}
