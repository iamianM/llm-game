import { expect, test } from "@playwright/test";
import { isDocumentedEvalCheck } from "../../lib/eval-checks";
import { runCostBreakdown } from "../../lib/eval-cost";
import { scenarioSummary } from "../../lib/eval-result";
import { evalShowcase, type EvalScenario } from "../../lib/eval-showcase";

test("reports the exact recorded token and cost breakdown", () => {
  expect(evalShowcase).not.toBeNull();
  const cost = runCostBreakdown(evalShowcase!);
  expect(cost.agentTokens).toBe(153_319);
  expect(cost.judgeTokens).toBe(213_872);
  expect(cost.totalTokens).toBe(367_191);
  expect(cost.exactCost).toBeCloseTo(0.08329272);
  expect(cost.agentCost.total_usd).toBeCloseTo(0.02210642);
  expect(cost.judgeCost.total_usd).toBeCloseTo(0.0611863);
});

test("explains deterministic failures separately from the thread evaluation", () => {
  const scenario = {
    id: "mixed-result",
    title: "Mixed result",
    question: "Did every check pass?",
    category: "conversation",
    goal: "Protect mixed-result wording.",
    status: "fail",
    judge: { result: "pass", reason: "The story stayed coherent.", evidence: null, model: "judge-model", reasoning_effort: "low", latency_ms: 1, total_tokens: 1, criteria: [], criterion_findings: [] },
    turns: [{
      id: "turn-1",
      action: "start_conversation | target chloe",
      status: "fail",
      golden: { calls: [] },
      story: { engine_result: null, relationship_changes: [], dialogue: null, narration: null, choices: [], events: [], memories: [], resort_changes: null },
      checks: [{ id: "rule", kind: "deterministic", result: "fail", reason: "A rule failed.", evidence: null }],
      traces: [],
    }],
  } satisfies EvalScenario;

  expect(scenarioSummary(scenario)).toBe("1 deterministic check failed.");
});

test("documents every deterministic check in the published run", () => {
  const ids = evalShowcase!.scenarios.flatMap((scenario) => scenario.turns.flatMap((turn) => turn.checks.map((check) => check.id)));
  expect(ids.filter((id) => !isDocumentedEvalCheck(id))).toEqual([]);
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
    await expect(page.getByText("71", { exact: true })).toBeVisible();
    await expect(page.getByText("367,191", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/153,319 tokens/)).toBeVisible();
    await expect(page.getByText(/213,872 tokens/)).toBeVisible();
    await expect(page.getByText("$0.08", { exact: true })).toBeVisible();
    await expect(page.getByText("Reviewed, checked-in showcase.json", { exact: true })).toHaveCount(0);
    await expect(page.getByText("Source revision", { exact: true })).toHaveCount(0);
    await expect(page.getByText("Can the game's AI stay in character?")).toHaveCount(0);
    await expect(page.getByText("See it work")).toHaveCount(0);
    await expect(page.getByText("thread_acceptance")).toHaveCount(0);
    await expect(page.locator("audio")).toHaveCount(0);

    await page.getByRole("link", { name: /View (scenarios|failures)/ }).click();
    await expect(page).toHaveURL(/conversation-continuity-exit$/);
    await expect(page.getByRole("heading", { name: "Conversation Continuity And Exit" })).toBeVisible();
    await expect(page.getByText("thread_acceptance")).toHaveCount(0);
    expect(errors).toEqual([]);
  });

  test("compares expected and actual output beside evaluation reasons", async ({ page }, testInfo) => {
    await page.goto("/evals/scenarios/interruption-accept");
    await expect(page.getByRole("heading", { name: "Scenario explorer" })).toHaveCount(0);
    await expect(page.getByText("LLM call · thread judge", { exact: true })).toBeVisible();
    await page.getByText("Why it passed", { exact: true }).click();
    await expect(page.getByText("What the judge reviewed", { exact: true })).toBeVisible();
    const firstField = page.getByTestId("output-comparison-field").first();
    const comparisonLabels = testInfo.project.name === "mobile" ? firstField : page;
    await expect(comparisonLabels.getByText("Reviewed target", { exact: true }).first()).toBeVisible();
    await expect(comparisonLabels.getByText("Actual output", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("You wanted something?", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Heartbreaker Voice", { exact: true })).toHaveCount(1);
    await expect(page.getByText("writes the player and NPC exchange", { exact: true })).toHaveCount(1);
    await expect(page.getByText("What may vary", { exact: true })).toHaveCount(0);
    await expect(page.getByText("Deterministic engine & schema checks", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Final result · after engine assembly", { exact: true })).toHaveCount(0);
    await expect(page.getByText("Choices used by the game", { exact: true })).toBeVisible();
    await expect(page.getByText("Model", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Latency", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Tokens", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Cost", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Token breakdown", { exact: true }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "Run trace" })).toHaveCount(0);
    await expect(page.getByText("Raw check names")).toHaveCount(0);
    await expect(page.getByText("response_id")).toHaveCount(0);
    await expect(page.getByText("prompt_sha256")).toHaveCount(0);
  });

  test("keeps each reference call paired with its actual call", async ({ page }, testInfo) => {
    await page.goto("/evals/scenarios/all-starting-npc-first-chats");
    const firstPair = page.getByTestId("output-comparison-field").first();
    const reference = await firstPair.locator('[data-call-source="reference"]').boundingBox();
    const actual = await firstPair.locator('[data-call-source="actual"]').boundingBox();
    expect(reference).not.toBeNull();
    expect(actual).not.toBeNull();
    if (testInfo.project.name === "mobile") {
      expect(actual!.y).toBeGreaterThanOrEqual(reference!.y + reference!.height);
    } else {
      expect(Math.abs(reference!.y - actual!.y)).toBeLessThanOrEqual(1);
    }
  });

  test("uses actual-thread criteria for dependent calls", async ({ page }) => {
    await page.goto("/evals/scenarios/conversation-continuity-exit");
    await expect(page.getByText("Selected intent", { exact: true }).first()).toBeVisible();
    const contextualTarget = page.getByTestId("criteria-comparison").first();
    await expect(contextualTarget.getByText("Reviewed criteria", { exact: true })).toBeVisible();
    await expect(contextualTarget.getByText("Actual output from this thread", { exact: true })).toBeVisible();
    await expect(contextualTarget.getByText(/responds to Chloe's actual opening answer/i)).toBeVisible();
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
    await expect(page.getByRole("heading", { name: /Chloe/ }).first()).toBeVisible();
    const remaining = page.getByText("Show remaining 15 turns", { exact: true });
    await expect(remaining).toBeVisible();
    await remaining.click();
    await expect(page.getByRole("heading", { name: /Blake/ }).last()).toBeVisible();
  });

  test("fits the mobile viewport without a scenario rail", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile", "Mobile-specific contract.");
    await page.goto("/evals");
    await expect(page.getByRole("heading", { name: "Evaluation overview" })).toBeVisible();
    await expect(page.getByRole("link", { name: /View (scenarios|failures)/ })).toBeVisible();
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
    await expect(page.getByTestId("output-comparison-field").first().getByText("Actual output", { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Run trace" })).toHaveCount(0);
    expect(await page.getByTestId("eval-page").evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  });
});
