"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useParams, useRouter } from "next/navigation";
import { getBlackfenSession, submitBlackfenTurn } from "../../../../lib/blackfen/api";
import type { BlackfenState } from "../../../../lib/blackfen/types";

export default function BlackfenPlayPage() {
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();
  const sessionId = params.sessionId;
  const [state, setState] = useState<BlackfenState | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [narration, setNarration] = useState("");
  const [rolls, setRolls] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getBlackfenSession(sessionId)
      .then((session) => {
        if (cancelled) return;
        setState(session.state);
        setSuggestions(session.suggestions);
        setNarration(session.state.last_narration ?? "Rain taps the shutters of the Bent Nail Inn. The road north waits outside.");
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load session.");
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const activeImage = state?.monsters_here[0]?.image ?? state?.npcs_here[0]?.image ?? state?.current_location.image;
  const visibleNarration = useMemo(() => narration.split("\n").filter(Boolean), [narration]);

  async function submit(text: string) {
    const trimmed = text.trim();
    if (!trimmed || busy || !state) return;
    setBusy(true);
    setError(null);
    try {
      const turn = await submitBlackfenTurn(sessionId, trimmed);
      setState(turn.state);
      setSuggestions(turn.suggestions);
      setNarration(turn.narration);
      setRolls(turn.rolls);
      setInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "That action failed.");
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submit(input);
  }

  if (!state) {
    return <main className="grid min-h-svh place-items-center bg-[#10110d] text-stone-100">Loading Blackfen Road...</main>;
  }

  return (
    <main className="grid h-svh overflow-hidden bg-[#10110d] text-stone-100 lg:grid-cols-[minmax(0,1fr)_390px]">
      <section className="relative min-h-0">
        <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: `url(${state.current_location.image})` }} />
        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(11,12,9,0.28),rgba(11,12,9,0.88)),radial-gradient(circle_at_68%_30%,rgba(226,173,81,0.12),transparent_30%)]" />
        <div className="relative flex h-full flex-col justify-between p-4 sm:p-6">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <button className="rounded border border-stone-500/70 bg-stone-950/70 px-3 py-2" onClick={() => router.push("/blackfen")}>New Run</button>
            <span className="rounded border border-stone-500/70 bg-stone-950/70 px-3 py-2">Seed {state.seed}</span>
            <span className="rounded border border-stone-500/70 bg-stone-950/70 px-3 py-2">Hash {state.state_hash}</span>
            <span className="rounded border border-amber-300/70 bg-amber-300/15 px-3 py-2 uppercase">{state.status}</span>
          </div>
          <div className="grid max-h-[82svh] grid-cols-1 gap-4 lg:grid-cols-[320px_minmax(0,700px)]">
            <div className="hidden self-end lg:block">
              {activeImage ? <img src={activeImage} alt="" className="max-h-[64svh] w-full rounded-md object-cover shadow-2xl" /> : null}
            </div>
            <div className="self-end rounded-md border border-stone-600/70 bg-stone-950/82 p-4 shadow-2xl backdrop-blur">
              <p className="text-sm uppercase tracking-[0.22em] text-amber-300">{state.current_location.kind}</p>
              <h1 className="mt-1 text-3xl font-semibold">{state.current_location.name}</h1>
              <p className="mt-2 text-sm leading-6 text-stone-300">{state.current_location.description}</p>
              <div className="mt-4 space-y-2 text-base leading-7">
                {visibleNarration.map((line, index) => <p key={`${line}-${index}`}>{line}</p>)}
              </div>
              {rolls.length ? <div className="mt-4 flex flex-wrap gap-2 text-xs text-stone-200">{rolls.map((roll, index) => <span key={index} className="rounded border border-stone-600 bg-stone-900 px-2 py-1">{String(roll.label)}: {String(roll.total)}{roll.target ? ` vs ${String(roll.target)}` : ""}</span>)}</div> : null}
              {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}
              <form onSubmit={onSubmit} className="mt-4 flex gap-2">
                <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="What do you do?" className="min-w-0 flex-1 rounded border border-stone-600 bg-stone-900 px-3 py-3 outline-none focus:border-amber-300" />
                <button disabled={busy || state.status !== "active"} className="rounded bg-amber-300 px-4 py-3 font-semibold text-stone-950 disabled:opacity-60">Send</button>
              </form>
              <div className="mt-3 flex flex-wrap gap-2">
                {suggestions.map((suggestion) => <button key={suggestion} onClick={() => void submit(suggestion)} disabled={busy || state.status !== "active"} className="rounded border border-stone-600 px-2 py-1 text-sm text-stone-200 hover:border-amber-300 disabled:opacity-50">{suggestion}</button>)}
              </div>
            </div>
          </div>
        </div>
      </section>
      <aside className="hidden min-h-0 border-l border-stone-700/80 bg-stone-950 p-4 lg:block">
        <Panel title="Party"><StatLine name={state.player.name} actor={state.player} /><StatLine name={state.companion.name} actor={state.companion} /><p className="mt-2 text-sm text-stone-400">Elian stance: {state.companion_stance}</p></Panel>
        <Panel title="People And Threats">{state.npcs_here.map((npc) => <p key={npc.id} className="text-sm"><span className="text-stone-100">{npc.name}</span> <span className="text-stone-400">{npc.role}</span></p>)}{state.monsters_here.map((monster) => <p key={monster.id} className="text-sm text-red-200">{monster.name} HP {monster.hp}</p>)}</Panel>
        <Panel title="Inventory"><div className="grid grid-cols-2 gap-2">{state.inventory.map((item) => <span key={item.id} className="rounded border border-stone-700 p-2 text-xs">{item.name}</span>)}</div></Panel>
        <Panel title="Journal"><div className="max-h-[22svh] space-y-2 overflow-auto text-sm text-stone-300">{state.journal.length ? state.journal.map((line, index) => <p key={index}>{line}</p>) : <p>No leads recorded yet.</p>}</div></Panel>
      </aside>
    </main>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return <section className="mb-4 rounded border border-stone-700 bg-stone-900/60 p-3"><h2 className="mb-2 text-sm font-semibold uppercase tracking-[0.18em] text-amber-300">{title}</h2>{children}</section>;
}

function StatLine({ name, actor }: { name: string; actor: { hp: number; max_hp: number; armor_class: number } }) {
  const pct = Math.max(0, Math.min(100, (actor.hp / actor.max_hp) * 100));
  return <div className="mb-3"><div className="flex justify-between text-sm"><span>{name}</span><span>AC {actor.armor_class} | HP {actor.hp}/{actor.max_hp}</span></div><div className="mt-1 h-2 rounded bg-stone-800"><div className="h-2 rounded bg-emerald-400" style={{ width: `${pct}%` }} /></div></div>;
}

