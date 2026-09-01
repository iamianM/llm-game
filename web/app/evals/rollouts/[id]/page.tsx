import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { EvalHeader } from "../../../../components/evals/EvalHeader";
import { ScenarioDetail } from "../../../../components/evals/ScenarioDetail";
import { evalRollout, getRolloutScenario } from "../../../../lib/eval-rollout";
import styles from "../../evals.module.css";

type PageProps = { params: Promise<{ id: string }> };

export function generateStaticParams() {
  return evalRollout?.scenarios.map((scenario) => ({ id: scenario.id })) ?? [];
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const scenario = getRolloutScenario((await params).id);
  return scenario ? { title: `${scenario.title} Causal Rollout | Paradise Hearts AI Evals`, description: scenario.question } : {};
}

export default async function RolloutPage({ params }: PageProps) {
  const scenario = getRolloutScenario((await params).id);
  if (!scenario) return notFound();
  return (
    <div className={styles.page} data-testid="eval-page">
      <EvalHeader />
      <main className={styles.rolloutMain}>
        <ScenarioDetail scenario={scenario} executionModel="causal_rollout" />
      </main>
    </div>
  );
}
