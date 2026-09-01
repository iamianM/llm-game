import type { EvalScenario } from "./eval-showcase";

export function scenarioSummary(scenario: EvalScenario) {
  const checks = scenario.turns
    .flatMap((turn) => turn.checks)
    .filter((check) => check.id !== "exactly_one_exit");
  const failed = checks.filter((check) => check.result === "fail").length;
  const review = checks.filter((check) => check.result === "cannot_determine").length;
  if (scenario.status === "pass") return `All ${checks.length} deterministic checks and the scenario evaluation passed.`;
  if (failed) return `${failed} deterministic ${failed === 1 ? "check" : "checks"} failed.`;
  if (review) return `${review} deterministic ${review === 1 ? "check needs" : "checks need"} human review.`;
  if (scenario.judge?.result === "fail") return `All ${checks.length} deterministic checks passed; the scenario judge failed.`;
  if (scenario.judge?.result === "cannot_determine") return `All ${checks.length} deterministic checks passed; the scenario judge needs review.`;
  return "This scenario needs review.";
}
