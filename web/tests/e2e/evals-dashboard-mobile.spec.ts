import { expect, test } from "@playwright/test";
import { runCostBreakdown } from "../../lib/eval-cost";
import { scenarioSummary } from "../../lib/eval-result";
import { evalShowcase, type EvalScenario } from "../../lib/eval-showcase";

test("reports the exact recorded token and cost breakdown", () => {
  expect(evalShowcase).not.toBeNull();
  const cost = runCostBreakdown(evalShowcase!);
  expect(cost.agentTokens).toBe(232_255);
  expect(cost.judgeTokens).toBe(223_115);
  expect(cost.totalTokens).toBe(455_370);
  expect(cost.exactCost).toBeCloseTo(0.09868617);
  expect(cost.agentCost.total_usd).toBeCloseTo(0.0338854);
  expect(cost.judgeCost.total_usd).toBeCloseTo(0.06480077);
});

test("explains deterministic failures separately from the thread evaluation", () => {
  const scenario = {
    id: "mixed-result",
    title: "Mixed result",
    question: "Did every check pass?",
    category: "conversation",
    goal: "Protect mixed-result wording.",
    status: "fail",
    judge: { result: "pass", reason: "The story stayed coherent.", evidence: null, model: "judge-model", reasoning_effort: "low", latency_ms: 1, total_tokens: 1, criteria: [] },
    turns: [{
      id: "turn-1",
      action: "start_conversation | target chloe",
      status: "fail",
      golden: { criteria: "The exchange should remain coherent.", calls: [] },
      story: { engine_result: null, relationship_changes: [], dialogue: null, narration: null, choices: [], events: [], memories: [], resort_changes: null },
      checks: [{ id: "rule", kind: "deterministic", result: "fail", reason: "A rule failed.", evidence: null }],
      traces: [],
    }],
  } satisfies EvalScenario;

  expect(scenarioSummary(scenario)).toBe("1 deterministic check failed.");
});

test.describe("public eval dashboard", () => {
  test("shows the run result without marketing copy or game audio", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });

    await page.goto("/evals");

    await expect(page.getByRole("heading", { name: "Evaluation overview" })).toBeVisible();
    await expect(page.getByText("24 passed", { exact: true })).toBeVisible();
    await expect(page.getByText("0 failed", { exact: true })).toBeVisible();
    await expect(page.getByText("86", { exact: true })).toBeVisible();
    await expect(page.getByText("82", { exact: true })).toBeVisible();
    await expect(page.getByText("455,370", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/232,255 tokens/)).toBeVisible();
    await expect(page.getByText(/223,115 tokens/)).toBeVisible();
    await expect(page.getByText("$0.10", { exact: true })).toBeVisible();
    await expect(page.getByText("Reviewed, checked-in showcase.json", { exact: true })).toHaveCount(0);
    await expect(page.getByText("Source revision", { exact: true })).toHaveCount(0);
    await expect(page.getByText("Can the game's AI stay in character?")).toHaveCount(0);
    await expect(page.getByText("See it work")).toHaveCount(0);
    await expect(page.getByText("thread_acceptance")).toHaveCount(0);
    await expect(page.locator("audio")).toHaveCount(0);

    await page.getByRole("link", { name: /View scenarios/ }).click();
    await expect(page).toHaveURL(/conversation-continuity-exit$/);
    await expect(page.getByRole("heading", { name: "Conversation Continuity And Exit" })).toBeVisible();
    await expect(page.getByText("What’s life like for you back home, Chloe?", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("thread_acceptance")).toHaveCount(0);
    expect(errors).toEqual([]);
  });

  test("compares expected and actual output beside evaluation reasons", async ({ page }) => {
    await page.goto("/evals/scenarios/interruption-accept");
    await expect(page.getByText("Thread judge · full scenario · gpt-5.6-luna", { exact: true })).toBeVisible();
    await expect(page.getByText(/faithfully .* accepted interruption/i).first()).toBeVisible();
    await expect(page.getByText("Reviewed golden · expected calls", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Actual calls · in order", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Of course, go ahead. You looked like you had something on your mind.", { exact: true })).toBeVisible();
    await expect(page.getByText("You’re all right, Liam—come sit down. What did you want to say?", { exact: true })).toBeVisible();
    await expect(page.getByText("Heartbreaker Voice", { exact: true })).toHaveCount(2);
    await expect(page.getByText("writes the player and NPC exchange", { exact: true })).toHaveCount(2);
    await expect(page.getByText("Comparison criteria", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Engine & schema checks", { exact: true }).first()).toBeVisible();

    await page.getByRole("link", { name: "Run trace" }).click();
    await expect(page).toHaveURL(/view=technical/);
    await expect(page.getByRole("heading", { name: "Run trace" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Output" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "MemoryBatch" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "Exchange", exact: true })).toBeVisible();
    await expect(page.getByRole("cell", { name: /gpt-5\.6-luna/i }).first()).toBeVisible();
    await expect(page.getByText("Raw check names")).toHaveCount(0);
    await expect(page.getByText("response_id")).toHaveCount(0);
    await expect(page.getByText("prompt_sha256")).toHaveCount(0);
  });

  test("supports search, deep links, and the no-results state", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name === "mobile", "Desktop sidebar owns search.");
    await page.goto("/evals/scenarios/private-chat-rejection");
    await expect(page.getByRole("heading", { name: "Private Chat (Rejection)" })).toBeVisible();
    const search = page.getByPlaceholder("Search scenarios");
    await search.fill("final vote");
    await expect(page.getByRole("link", { name: /Final Vote Finale/ })).toBeVisible();
    await search.fill("nothing has this name");
    await expect(page.getByText("No scenarios match.")).toBeVisible();
  });

  test("collapses the longest story until a reviewer asks for more", async ({ page }) => {
    await page.goto("/evals/scenarios/all-starting-npc-first-chats");
    const remaining = page.getByText("Show remaining 15 turns", { exact: true });
    await expect(remaining).toBeVisible();
    await remaining.click();
    await expect(page.getByRole("heading", { name: /Blake/ }).last()).toBeVisible();
  });

  test("fits the mobile viewport without a scenario rail", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile", "Mobile-specific contract.");
    await page.goto("/evals");
    await expect(page.getByRole("heading", { name: "Evaluation overview" })).toBeVisible();
    await expect(page.getByRole("link", { name: /View scenarios/ })).toBeVisible();
    await expect(page.locator("audio")).toHaveCount(0);
    expect(await page.getByTestId("eval-page").evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);

    await page.goto("/evals/scenarios/conversation-continuity-exit");
    await expect(page.getByLabel("Scenario category")).toBeVisible();
    await expect(page.getByLabel("Scenario", { exact: true })).toBeVisible();
    await page.getByLabel("Scenario category").selectOption("pairing_and_endings");
    await expect(page).toHaveURL(/final-vote-ending$/);
    await page.getByLabel("Scenario", { exact: true }).selectOption("opening-ceremony");
    await expect(page).toHaveURL(/opening-ceremony$/);
    expect(await page.getByTestId("eval-page").evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);

    await page.goto("/evals/scenarios/conversation-continuity-exit");
    await page.getByTestId("eval-page").evaluate((element) => { element.scrollTop = 900; });
    await page.getByRole("link", { name: "Run trace" }).click();
    await expect(page.getByText("Game agents")).toBeVisible();
    expect(await page.getByTestId("eval-page").evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  });
});
