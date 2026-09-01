import rawRollout from "../data/evals/rollout.json";
import { parseShowcase } from "./eval-showcase";

export const evalRollout = parseShowcase(rawRollout);

export function getRolloutScenario(id: string) {
  return evalRollout?.scenarios.find((scenario) => scenario.id === id) ?? null;
}
