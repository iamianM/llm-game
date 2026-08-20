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

test("music starts quiet and full slider volume stays capped", async ({ page }) => {
  await page.goto("/new-run");
  await page.getByRole("button", { name: /^Play as / }).click();
  await page.getByLabel("Open settings").click();

  const volume = page.getByLabel("Music volume");
  await expect(volume).toHaveValue("20");

  // Let the initial title-to-game crossfade finish so this exercises the
  // direct slider-update path as well as the fade path.
  await page.waitForTimeout(1_200);
  await volume.fill("100");
  await expect(volume).toHaveValue("100");

  await page.waitForTimeout(100);
  const playingVolumes = await page.locator("audio").evaluateAll((elements) =>
    elements
      .filter((element) => !(element as HTMLAudioElement).paused)
      .map((element) => (element as HTMLAudioElement).volume),
  );
  expect(playingVolumes.length).toBeGreaterThan(0);
  expect(Math.max(...playingVolumes)).toBeLessThanOrEqual(0.5);
});
