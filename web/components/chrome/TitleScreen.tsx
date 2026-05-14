"use client";

import Link from "next/link";
import { Heart, Sparkles } from "lucide-react";
import { Button } from "../ui/Button";

export function TitleScreen() {
  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden bg-bg px-6 text-center film-grain">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_20%,rgba(185,80,47,.26),transparent_34%),linear-gradient(180deg,#1c1612,#100c09)]" />
      <section className="relative max-w-2xl">
        <div className="mb-6 flex justify-center text-gold"><Sparkles size={34} /></div>
        <h1 className="font-display text-7xl font-bold tracking-tight text-[var(--card)] drop-shadow">
          Paradise Hearts
        </h1>
        <p className="mt-4 text-lg text-[var(--muted-on-dark)]">Make a Connection. Survive the Drama.</p>
        <div className="mx-auto mt-10 flex max-w-xs flex-col gap-3">
          <Link href="/new-run"><Button className="w-full">New Run</Button></Link>
          <Button disabled variant="secondary">Continue Run</Button>
          <Button disabled variant="secondary">The Reunion</Button>
        </div>
        <footer className="mt-12 flex items-center justify-center gap-2 text-xs text-[var(--muted-on-dark)]">
          <Heart size={14} /> MVP build - Heart Beats arrive in Phase 4
        </footer>
      </section>
    </main>
  );
}
