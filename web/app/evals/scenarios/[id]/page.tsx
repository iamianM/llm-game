import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { EvalHeader } from "../../../../components/evals/EvalHeader";
import { ScenarioDetail, type ScenarioView } from "../../../../components/evals/ScenarioDetail";
import { ScenarioNav } from "../../../../components/evals/ScenarioNav";
import { evalShowcase, getScenario } from "../../../../lib/eval-showcase";
import styles from "../../evals.module.css";

type PageProps = { params: Promise<{ id: string }>; searchParams: Promise<{ view?: string }> };

export function generateStaticParams() {
  return evalShowcase?.scenarios.map((scenario) => ({ id: scenario.id })) ?? [];
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const scenario = getScenario((await params).id);
  return scenario ? { title: `${scenario.title} | Paradise Hearts AI Evals`, description: scenario.question } : {};
}

export default async function ScenarioPage({ params, searchParams }: PageProps) {
  if (!evalShowcase) return notFound();
  const scenario = getScenario((await params).id);
  if (!scenario) return notFound();
  const requestedView = (await searchParams).view;
  const view: ScenarioView = requestedView === "technical" ? "technical" : "results";
  const summaries = evalShowcase.scenarios.map((item) => ({ id: item.id, title: item.title, category: item.category, status: item.status, turns: item.turns.length }));

  return (
    <div className={styles.page} data-testid="eval-page">
      <EvalHeader />
      <main className={styles.browserMain}>
        <header className={styles.browserIntro}>
          <div><p className={styles.eyebrow}>Evaluation results</p><h1>Scenario explorer</h1><p>Reviewed golden and actual agent results are shown together.</p></div>
        </header>
        <div className={styles.browserGrid}>
          <ScenarioNav scenarios={summaries} selectedId={scenario.id} />
          <ScenarioDetail scenario={scenario} showcase={evalShowcase} view={view} />
        </div>
      </main>
    </div>
  );
}
