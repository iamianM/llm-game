"use client";

import { Button } from "../ui/Button";
import { Pill } from "../ui/Pill";

type Props = {
  id: string;
  title: string;
  bonus: string;
  advantage: string;
  selected: boolean;
  onSelect: () => void;
};

export function ArchetypeCard({ title, bonus, advantage, selected, onSelect }: Props) {
  return (
    <article className={`rounded-[var(--r-lg)] border bg-card p-6 text-ink shadow-[var(--shadow-md)] transition ${selected ? "border-accent ring-2 ring-[var(--accent-soft)]" : "border-line"}`}>
      <div className="mb-5 grid h-16 w-16 place-items-center rounded-full bg-[var(--accent-soft)] font-display text-2xl font-bold text-accent">
        {title.slice(0, 2)}
      </div>
      <h2 className="font-display text-2xl font-semibold">{title}</h2>
      <div className="mt-3 flex gap-2"><Pill tone="accent">{bonus}</Pill></div>
      <p className="mt-4 min-h-16 text-sm leading-6 text-[var(--muted)]">{advantage}</p>
      <Button onClick={onSelect} className="mt-6 w-full">{selected ? "Picked" : "Pick"}</Button>
    </article>
  );
}
