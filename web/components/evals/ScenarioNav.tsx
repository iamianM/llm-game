"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import styles from "../../app/evals/evals.module.css";
import { CATEGORY_LABELS, CATEGORY_ORDER, type EvalCategory } from "../../lib/eval-showcase";

type ScenarioSummary = {
  id: string;
  title: string;
  category: EvalCategory;
  status: "pass" | "fail" | "cannot_determine";
  turns: number;
};

export function ScenarioNav({ scenarios, selectedId }: { scenarios: ScenarioSummary[]; selectedId: string }) {
  const router = useRouter();
  const selected = scenarios.find((scenario) => scenario.id === selectedId) ?? scenarios[0];
  const [query, setQuery] = useState("");
  const [mobileCategory, setMobileCategory] = useState<EvalCategory>(selected.category);
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return needle ? scenarios.filter((scenario) => scenario.title.toLowerCase().includes(needle)) : scenarios;
  }, [query, scenarios]);
  const mobileScenarios = scenarios.filter((scenario) => scenario.category === mobileCategory);

  function openScenario(id: string) {
    router.push(`/evals/scenarios/${id}`);
    document.querySelector(`.${styles.page}`)?.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <>
      <div className={styles.mobilePicker} aria-label="Browse scenarios">
        <select
          aria-label="Scenario category"
          value={mobileCategory}
          onChange={(event) => {
            const category = event.target.value as EvalCategory;
            setMobileCategory(category);
            const firstScenario = scenarios.find((scenario) => scenario.category === category);
            if (firstScenario) openScenario(firstScenario.id);
          }}
        >
          {CATEGORY_ORDER.map((category) => <option key={category} value={category}>{CATEGORY_LABELS[category]}</option>)}
        </select>
        <select aria-label="Scenario" value={mobileScenarios.some((item) => item.id === selectedId) ? selectedId : ""} onChange={(event) => openScenario(event.target.value)}>
          {!mobileScenarios.some((item) => item.id === selectedId) && <option value="">Choose a scenario</option>}
          {mobileScenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.title}</option>)}
        </select>
      </div>
      <aside className={styles.sidebar} aria-label="All evaluation scenarios">
        <input className={styles.search} type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search scenarios" />
        {CATEGORY_ORDER.map((category) => {
          const categoryScenarios = filtered.filter((scenario) => scenario.category === category);
          if (!categoryScenarios.length) return null;
          return (
            <section className={styles.categoryBlock} key={category}>
              <div className={styles.categoryTitle}><span>{CATEGORY_LABELS[category]}</span><span>{categoryScenarios.length}</span></div>
              <div className={styles.scenarioLinks}>
                {categoryScenarios.map((scenario) => (
                  <Link aria-current={scenario.id === selectedId ? "page" : undefined} className={`${styles.scenarioLink} ${scenario.id === selectedId ? styles.scenarioLinkActive : ""}`} data-status={scenario.status} href={`/evals/scenarios/${scenario.id}`} key={scenario.id}>
                    <span>{scenario.title}</span><span aria-label={scenario.status}>{scenario.status === "pass" ? "●" : "!"}</span>
                  </Link>
                ))}
              </div>
            </section>
          );
        })}
        {filtered.length === 0 && <p className={styles.empty}>No scenarios match.</p>}
      </aside>
    </>
  );
}
