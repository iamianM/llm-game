const { chromium, devices } = require("@playwright/test");
const fs = require("fs");
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ ...devices["Pixel 7"] });
  const page = await ctx.newPage();
  const home = "C:/Users/Mcian/projects/llm-game/_gamefeel/";
  fs.mkdirSync(home, { recursive: true });
  await page.goto("http://127.0.0.1:3001/");
  await page.waitForTimeout(900);
  await page.screenshot({ path: home + "m-01-title.png", fullPage: false });
  await page.click("text=New Run");
  await page.waitForTimeout(700);
  await page.screenshot({ path: home + "m-02-new-run.png", fullPage: false });
  try { await page.getByRole("button", { name: "Test mode" }).click(); } catch {}
  await page.waitForTimeout(300);
  try { await page.getByRole("button", { name: "Step into Sunset Bay" }).click(); } catch {}
  await page.waitForURL(/\/play\//);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: home + "m-03-stage.png", fullPage: false });
  // Pick first choice
  await page.locator('[data-role="choice"]').first().click();
  await page.waitForTimeout(3000);
  // Try continue
  try { await page.locator('text=Continue').click({ timeout: 4000 }); } catch {}
  await page.waitForTimeout(1500);
  await page.screenshot({ path: home + "m-04-intro.png", fullPage: false });
  await browser.close();
  console.log("DONE");
})();
