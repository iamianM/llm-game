import { expect, test, type Page } from "@playwright/test";

const forbiddenVisibleCopy = [
  /\bCasa Amor\b/i,
  /\bWild Hearts\b/i,
  /\bFirst Pairing\b/i,
  /\bHeart Appeal\b/i,
  /\bGuest card\b/i,
  /\bAudience\s*[+-]/i,
  /\brecoupling\b/i,
  /\bgrafting\b/i,
  /\bgraft\b/i,
  /\bbombshell\b/i,
  /\bislanders\b/i,
  /\bthe villa\b/i,
  /\bdumped\b/i,
  /\bmugged off\b/i,
  /\bpied off\b/i,
  /I've got a text/i,
  /\b\d{2,3}m\b/
];

test("player-facing pages use Paradise Hearts vocabulary", async ({ page }) => {
  await page.goto("/");
  await assertCleanCopy(page);

  await page.getByRole("link", { name: "New Run" }).click();
  await assertCleanCopy(page);

  await page.getByRole("button", { name: "Test mode" }).click();
  await page.getByRole("button", { name: "Step into Sunset Bay" }).click();
  await expect(page.getByTestId("choice-menu")).toBeVisible();
  await assertCleanCopy(page);

  await page.getByLabel("Open right rail").click();
  await assertCleanCopy(page);
});

async function assertCleanCopy(page: Page) {
  const visibleText = await page.locator("body").innerText();
  for (const pattern of forbiddenVisibleCopy) {
    expect(visibleText, `Unexpected brand residue matched ${pattern}`).not.toMatch(pattern);
  }
}
