"use client";

import Link from "next/link";
import styles from "../../app/evals/evals.module.css";

type View = "results" | "technical";

export function ScenarioTabs({ scenarioId, view }: { scenarioId: string; view: View }) {
  function resetView() {
    window.setTimeout(() => document.getElementById("scenario-tabs")?.scrollIntoView({ block: "start" }), 0);
  }

  return (
    <nav className={styles.tabs} id="scenario-tabs" aria-label="Scenario detail">
      {(["results", "technical"] as const).map((item) => (
        <Link
          aria-current={view === item ? "page" : undefined}
          className={`${styles.tab} ${view === item ? styles.tabActive : ""}`}
          href={`/evals/scenarios/${scenarioId}${item === "results" ? "" : `?view=${item}`}`}
          key={item}
          onClick={resetView}
        >
          {item === "technical" ? "Run trace" : "Results"}
        </Link>
      ))}
    </nav>
  );
}
