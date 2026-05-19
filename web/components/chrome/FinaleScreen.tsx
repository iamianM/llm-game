"use client";

import Link from "next/link";
import type { SessionState } from "../../lib/types";
import { Avatar } from "../ui/Avatar";
import { Button } from "../ui/Button";

export function FinaleScreen({ state }: { state: SessionState }) {
  const playerCouple = state.couples.find((couple) => couple.is_player_couple);
  return (
    <main data-screen="finale" className="grid min-h-screen place-items-center bg-[linear-gradient(180deg,rgba(7,5,4,.4),rgba(7,5,4,.9)),url('/images/features/finale.webp')] bg-cover bg-center p-8 text-center text-[var(--card)]">
      <section className="max-w-3xl">
        <p className="font-hand text-4xl text-gold">Finale</p>
        <h1 className="mt-2 font-display text-7xl">Sunset Bay crowns its couple</h1>
        {playerCouple ? (
          <div className="mx-auto mt-10 flex max-w-xl items-center justify-center gap-8 rounded-[var(--r-xl)] border border-gold bg-white/10 p-8">
            <Avatar id={playerCouple.partner_a_id} name={playerCouple.partner_a_name} size="lg" />
            <div>
              <p className="font-display text-3xl">{playerCouple.partner_a_name} & {playerCouple.partner_b_name}</p>
              <p className="mt-2 text-gold">Couple strength {playerCouple.strength}</p>
            </div>
            <Avatar id={playerCouple.partner_b_id} name={playerCouple.partner_b_name} size="lg" />
          </div>
        ) : null}
        <p className="mt-8 text-lg text-[var(--muted-on-dark)]">Outcome: {state.outcome?.replaceAll("_", " ") ?? "complete"}</p>
        <p className="mt-2 text-gold">Heart Beats earned: 0 - The Reunion opens in Phase 4.</p>
        <Link href="/"><Button className="mt-8">New Run</Button></Link>
      </section>
    </main>
  );
}
