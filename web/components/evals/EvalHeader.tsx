"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "../../app/evals/evals.module.css";

export function EvalHeader() {
  const pathname = usePathname();
  return (
    <header className={styles.header}>
      <Link className={styles.brand} href="/">Paradise Hearts</Link>
      <nav className={styles.nav} aria-label="Evaluation navigation">
        <Link aria-current={pathname === "/evals" ? "page" : undefined} href="/evals">Overview</Link>
        <Link aria-current={pathname.startsWith("/evals/scenarios") ? "page" : undefined} href="/evals/scenarios">Scenarios</Link>
        <Link href="/">Play the game</Link>
      </nav>
    </header>
  );
}
