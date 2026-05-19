const { chromium } = require("@playwright/test");
const fs = require("fs");
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const home = "C:/Users/Mcian/projects/llm-game/_gamefeel/";
  fs.mkdirSync(home, { recursive: true });
  await page.goto("http://127.0.0.1:3001/");
  await page.waitForTimeout(800);
  await page.screenshot({ path: home + "01-title.png", fullPage: true });
  await page.click("text=New Run");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(400);
  await page.screenshot({ path: home + "02-new-run.png", fullPage: true });
  // Toggle Test mode for deterministic mock-LLM screenshots
  await page.getByRole("button", { name: "Test mode" }).click();
  await page.waitForTimeout(200);
  // Pick Heartthrob (might already be Picked from prior state)
  const pickBtn = page.getByRole("button", { name: /^Pick$/ }).first();
  if (await pickBtn.count() > 0) {
    await pickBtn.click();
  }
  await page.waitForTimeout(400);
  await page.getByRole("button", { name: "Step into Sunset Bay" }).click();
  await page.waitForURL(/\/play\//);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: home + "03-first-load.png", fullPage: true });
  await page.locator('[data-role="choice"]').first().click();
  await page.waitForTimeout(4000);
  await page.screenshot({ path: home + "04-after-first-pair.png", fullPage: true });
  try { await page.locator('text=Continue').click({ timeout: 4000 }); } catch {}
  await page.waitForTimeout(1500);
  await page.screenshot({ path: home + "05-stage.png", fullPage: true });
  await page.locator('[data-role="choice"]').first().click();
  await page.waitForTimeout(4500);
  await page.screenshot({ path: home + "06-dialogue.png", fullPage: true });
  for (let i = 0; i < 5; i++) {
    const choice = page.locator('[data-role="choice"]').first();
    if (await choice.count() === 0) break;
    await choice.click();
    await page.waitForTimeout(3000);
  }
  await page.screenshot({ path: home + "07-mid-flow.png", fullPage: true });
  try {
    await page.getByLabel("Open right rail").click();
    await page.waitForTimeout(700);
    await page.screenshot({ path: home + "08-rail.png", fullPage: true });
    const profileBtns = await page.locator('button[aria-label*="profile"]').all();
    if (profileBtns.length > 0) {
      await profileBtns[0].click();
      await page.waitForTimeout(700);
      await page.screenshot({ path: home + "09-popout.png", fullPage: true });
    }
  } catch (e) { console.log("Rail issue:", e.message); }
  try {
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);
    await page.getByLabel("Open settings").click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: home + "10-settings.png", fullPage: true });
  } catch (e) { console.log("Settings issue:", e.message); }
  await browser.close();
  console.log("DONE");
})();
