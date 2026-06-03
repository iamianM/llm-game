"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { newBlackfenSession } from "../../lib/blackfen/api";
import { useUiStore } from "../../lib/store";
import type { BlackfenClassId } from "../../lib/blackfen/types";

const classes: Array<{ id: BlackfenClassId; label: string; body: string }> = [
  { id: "fighter", label: "Fighter", body: "Hard to kill, direct in a fight, best for a first road." },
  { id: "rogue", label: "Rogue", body: "Quick, curious, and better at reading danger before it reads you." },
  { id: "mage", label: "Mage", body: "Fragile but strange, with a hotter answer to old dead things." }
];

export default function BlackfenHome() {
  const router = useRouter();
  const [name, setName] = useState("Mara");
  const [classId, setClassId] = useState<BlackfenClassId>("fighter");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const useLive = useUiStore((s) => s.useLiveLlm);
  const setUseLive = useUiStore((s) => s.setUseLiveLlm);
  const mockLlm = !useLive;

  useEffect(() => {
    document.title = "Blackfen Road";
  }, []);

  async function startRun() {
    setBusy(true);
    setError(null);
    try {
      const session = await newBlackfenSession({ classId, playerName: name, seed: 42, mockLlm });
      router.push(`/blackfen/play/${session.session_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start Blackfen Road.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-svh overflow-hidden bg-[#10110d] text-stone-100">
      <section className="relative grid min-h-svh grid-cols-1 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="absolute inset-0 bg-[url('/images/blackfen/location-blackfen-village.png')] bg-cover bg-center opacity-45" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_24%_20%,rgba(218,170,85,0.22),transparent_32%),linear-gradient(90deg,rgba(12,13,10,0.96),rgba(12,13,10,0.72),rgba(12,13,10,0.9))]" />
        <div className="relative flex min-h-[46svh] flex-col justify-end px-6 pb-8 pt-10 sm:px-10 lg:min-h-svh lg:px-14 lg:pb-16">
          <p className="text-sm uppercase tracking-[0.28em] text-amber-300">AI Dungeon Master Roguelike</p>
          <h1 className="mt-4 max-w-3xl text-5xl font-semibold leading-none sm:text-7xl">Blackfen Road</h1>
          <p className="mt-5 max-w-2xl text-lg leading-7 text-stone-200">
            A rain-soaked frontier village, a missing caravan, and a bell that the dead are afraid to hear.
          </p>
        </div>
        <div className="relative flex items-center px-4 pb-6 sm:px-8 lg:px-12">
          <div className="w-full rounded-md border border-stone-600/60 bg-stone-950/78 p-4 shadow-2xl backdrop-blur sm:p-5">
            <label className="text-sm text-stone-300" htmlFor="blackfen-name">Name</label>
            <input
              id="blackfen-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="mt-2 w-full rounded border border-stone-600 bg-stone-900 px-3 py-2 text-base outline-none focus:border-amber-300"
            />
            <div className="mt-4 grid gap-2">
              {classes.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => setClassId(option.id)}
                  className={`rounded border p-3 text-left transition ${
                    classId === option.id ? "border-amber-300 bg-amber-300/12" : "border-stone-700 bg-stone-900/80 hover:border-stone-400"
                  }`}
                >
                  <span className="block text-base font-semibold">{option.label}</span>
                  <span className="mt-1 block text-sm text-stone-300">{option.body}</span>
                </button>
              ))}
            </div>
            <div className="mt-4 flex items-center justify-between gap-3 rounded border border-stone-700 bg-stone-900/70 p-3">
              <span className="text-sm text-stone-300">Story engine</span>
              <div className="flex rounded border border-stone-600 bg-stone-950 p-1 text-sm">
                <button
                  type="button"
                  aria-pressed={!useLive}
                  onClick={() => setUseLive(false)}
                  className={`rounded px-3 py-1.5 ${!useLive ? "bg-amber-300 text-stone-950" : "text-stone-300 hover:text-stone-100"}`}
                >
                  Demo
                </button>
                <button
                  type="button"
                  aria-pressed={useLive}
                  onClick={() => setUseLive(true)}
                  className={`rounded px-3 py-1.5 ${useLive ? "bg-amber-300 text-stone-950" : "text-stone-300 hover:text-stone-100"}`}
                >
                  Live LLM
                </button>
              </div>
            </div>
            {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}
            <button
              type="button"
              onClick={startRun}
              disabled={busy}
              className="mt-5 w-full rounded bg-amber-300 px-4 py-3 font-semibold text-stone-950 transition hover:bg-amber-200 disabled:opacity-60"
            >
              {busy ? "Opening the road" : "Start Run"}
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
