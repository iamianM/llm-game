"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useParams, useRouter } from "next/navigation";
import { getBlackfenSession, submitBlackfenTurn } from "../../../../lib/blackfen/api";
import type { BlackfenActor, BlackfenItem, BlackfenMonster, BlackfenState, BlackfenTurnLogEntry } from "../../../../lib/blackfen/types";

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
  const isEnded = state?.status !== "active";

  useEffect(() => {
    document.title = "Blackfen Road";
  }, []);

  async function submit(text: string) {
    const trimmed = text.trim();
    if (!trimmed || busy || !state || state.status !== "active") return;
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
    <main className="min-h-svh bg-[#10110d] text-stone-100 lg:grid lg:h-svh lg:grid-cols-[minmax(0,1fr)_390px] lg:overflow-hidden">
      <section className="relative min-h-svh lg:min-h-0">
        <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: `url(${state.current_location.image})` }} />
        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(11,12,9,0.36),rgba(11,12,9,0.92)),radial-gradient(circle_at_68%_30%,rgba(226,173,81,0.12),transparent_30%)]" />
        <div className="relative flex min-h-svh flex-col gap-4 p-4 sm:p-6 lg:h-full lg:min-h-0 lg:justify-between">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <button className="rounded border border-stone-500/70 bg-stone-950/70 px-3 py-2" onClick={() => router.push("/blackfen")}>New Run</button>
            <span className="rounded border border-stone-500/70 bg-stone-950/70 px-3 py-2">Seed {state.seed}</span>
            <span className="rounded border border-amber-300/70 bg-amber-300/15 px-3 py-2 uppercase">{state.status}</span>
            <details className="rounded border border-stone-500/70 bg-stone-950/70 px-3 py-2">
              <summary className="cursor-pointer">Debug</summary>
              <p className="mt-2 font-mono text-xs text-stone-300">Hash {state.state_hash}</p>
            </details>
          </div>

          <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,700px)] lg:self-end">
            <div className="hidden self-end lg:block">
              {activeImage ? <img src={activeImage} alt="" className="max-h-[64svh] w-full rounded-md object-cover shadow-2xl" /> : null}
            </div>
            <div className="self-end rounded-md border border-stone-600/70 bg-stone-950/85 p-4 shadow-2xl backdrop-blur">
              <p className="text-sm uppercase tracking-[0.22em] text-amber-300">{state.current_location.kind}</p>
              <h1 className="mt-1 text-3xl font-semibold">{state.current_location.name}</h1>
              <p className="mt-2 text-sm leading-6 text-stone-300">{state.current_location.description}</p>
              <CompactStatus state={state} />
              <ThreatList monsters={state.monsters_here} compact />
              <div className="mt-4 space-y-2 text-base leading-7">
                {visibleNarration.map((line, index) => <p key={`${line}-${index}`}>{line}</p>)}
              </div>
              {rolls.length ? <div className="mt-4 flex flex-wrap gap-2 text-xs text-stone-200">{rolls.map((roll, index) => <RollChip key={index} roll={roll} />)}</div> : null}
              {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}
              {isEnded ? <TerminalPanel state={state} onNewRun={() => router.push("/blackfen")} /> : null}
              <form onSubmit={onSubmit} className="mt-4 flex gap-2">
                <input
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder={isEnded ? "This run is over." : "What do you do?"}
                  disabled={isEnded}
                  className="min-w-0 flex-1 rounded border border-stone-600 bg-stone-900 px-3 py-3 outline-none focus:border-amber-300 disabled:opacity-60"
                />
                <button disabled={busy || isEnded} className="rounded bg-amber-300 px-4 py-3 font-semibold text-stone-950 disabled:opacity-60">Send</button>
              </form>
              <div className="mt-3 flex flex-wrap gap-2">
                {suggestions.map((suggestion) => <button key={suggestion} onClick={() => void submit(suggestion)} disabled={busy || isEnded} className="rounded border border-stone-600 px-2 py-1 text-sm text-stone-200 hover:border-amber-300 disabled:opacity-50">{suggestion}</button>)}
              </div>
            </div>
          </div>

          <div className="grid gap-3 pb-4 lg:hidden">
            <Panel title="Party"><StatLine name={state.player.name} actor={state.player} /><StatLine name={state.companion.name} actor={state.companion} /><p className="mt-2 text-sm text-stone-400">Elian stance: {state.companion_stance}</p></Panel>
            <Panel title="People And Threats"><People state={state} /></Panel>
            <Panel title="Inventory"><InventoryList inventory={state.inventory} /></Panel>
            <Panel title="Turn Log"><TurnLog turns={state.recent_turns} /></Panel>
          </div>
        </div>
      </section>
      <aside className="hidden min-h-0 overflow-auto border-l border-stone-700/80 bg-stone-950 p-4 lg:block">
        <Panel title="Party"><StatLine name={state.player.name} actor={state.player} /><StatLine name={state.companion.name} actor={state.companion} /><p className="mt-2 text-sm text-stone-400">Elian stance: {state.companion_stance}</p></Panel>
        <Panel title="People And Threats"><People state={state} /></Panel>
        <Panel title="Inventory"><InventoryList inventory={state.inventory} /></Panel>
        <Panel title="Journal"><JournalList journal={state.journal} /></Panel>
        <Panel title="Turn Log"><TurnLog turns={state.recent_turns} /></Panel>
      </aside>
    </main>
  );
}

function CompactStatus({ state }: { state: BlackfenState }) {
  return (
    <div className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
      <MiniStat label={state.player.name} hp={state.player.hp} maxHp={state.player.max_hp} />
      <MiniStat label={state.companion.name} hp={state.companion.hp} maxHp={state.companion.max_hp} />
    </div>
  );
}

function MiniStat({ label, hp, maxHp }: { label: string; hp: number; maxHp: number }) {
  const pct = Math.max(0, Math.min(100, (hp / maxHp) * 100));
  return (
    <div className="rounded border border-stone-700 bg-stone-900/80 p-2">
      <div className="flex justify-between gap-2"><span>{label}</span><span>HP {hp}/{maxHp}</span></div>
      <div className="mt-1 h-2 rounded bg-stone-800"><div className="h-2 rounded bg-emerald-400" style={{ width: `${pct}%` }} /></div>
    </div>
  );
}

function ThreatList({ monsters, compact = false }: { monsters: BlackfenMonster[]; compact?: boolean }) {
  if (!monsters.length) return null;
  return (
    <div className={compact ? "mt-3 grid gap-2 sm:grid-cols-2" : "space-y-2"}>
      {monsters.map((monster, index) => (
        <div key={monster.id} className="rounded border border-red-300/40 bg-red-950/35 p-2">
          <div className="flex justify-between gap-2 text-sm text-red-100">
            <span>{monster.name} {letterLabel(index)}</span>
            <span>HP {monster.hp}</span>
          </div>
          <div className="mt-1 h-2 rounded bg-stone-800"><div className="h-2 rounded bg-red-400" style={{ width: `${Math.max(8, Math.min(100, monster.hp * 7))}%` }} /></div>
        </div>
      ))}
    </div>
  );
}

function People({ state }: { state: BlackfenState }) {
  return (
    <div className="space-y-2">
      {state.npcs_here.map((npc) => <p key={npc.id} className="text-sm"><span className="text-stone-100">{npc.name}</span> <span className="text-stone-400">{npc.role}</span></p>)}
      <ThreatList monsters={state.monsters_here} />
      {!state.npcs_here.length && !state.monsters_here.length ? <p className="text-sm text-stone-400">No one else is close enough to act.</p> : null}
    </div>
  );
}

function InventoryList({ inventory }: { inventory: BlackfenItem[] }) {
  return <div className="grid grid-cols-2 gap-2">{inventory.map((item) => <span key={item.id} className="rounded border border-stone-700 p-2 text-xs">{item.name}</span>)}</div>;
}

function JournalList({ journal }: { journal: string[] }) {
  return <div className="max-h-[22svh] space-y-2 overflow-auto text-sm text-stone-300">{journal.length ? journal.map((line, index) => <p key={index}>{line}</p>) : <p>No leads recorded yet.</p>}</div>;
}

function TurnLog({ turns }: { turns: BlackfenTurnLogEntry[] }) {
  if (!turns.length) return <p className="text-sm text-stone-400">No turns yet.</p>;
  return (
    <div className="max-h-[26svh] space-y-2 overflow-auto text-sm">
      {turns.map((turn) => (
        <div key={turn.turn_index} className="rounded border border-stone-700 bg-stone-950/60 p-2">
          <p className="text-stone-400">#{turn.turn_index} {turn.raw_text}</p>
          <p>{turn.summary}</p>
          {turn.damage_to_player || turn.damage_to_companion || turn.damage_to_enemies ? <p className="mt-1 text-xs text-amber-200">Damage: you {turn.damage_to_player}, Elian {turn.damage_to_companion}, enemies {turn.damage_to_enemies}</p> : null}
        </div>
      ))}
    </div>
  );
}

function TerminalPanel({ state, onNewRun }: { state: BlackfenState; onNewRun: () => void }) {
  const title = state.status === "victory" ? "The Bell Falls Silent" : "The Road Claims You";
  return (
    <div className="mt-4 rounded border border-amber-300/60 bg-amber-300/12 p-3">
      <h2 className="text-lg font-semibold text-amber-200">{title}</h2>
      <p className="mt-1 text-sm text-stone-200">Final stats: turn {state.turn_index}, seed {state.seed}, {state.player.name} HP {state.player.hp}/{state.player.max_hp}, Elian HP {state.companion.hp}/{state.companion.max_hp}.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button onClick={onNewRun} className="rounded bg-amber-300 px-3 py-2 text-sm font-semibold text-stone-950">New Run</button>
        <button onClick={() => void navigator.clipboard.writeText(String(state.seed))} className="rounded border border-stone-500 px-3 py-2 text-sm">Copy Seed</button>
      </div>
    </div>
  );
}

function RollChip({ roll }: { roll: Record<string, unknown> }) {
  const modifier = Number(roll.modifier ?? 0);
  const sign = modifier >= 0 ? "+" : "";
  const target = roll.target ? ` vs ${String(roll.target)}` : "";
  return <span className="rounded border border-stone-600 bg-stone-900 px-2 py-1">{String(roll.label)}: d20 {sign}{modifier} = {String(roll.total)}{target}</span>;
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return <section className="rounded border border-stone-700 bg-stone-900/72 p-3"><h2 className="mb-2 text-sm font-semibold uppercase tracking-[0.18em] text-amber-300">{title}</h2>{children}</section>;
}

function StatLine({ name, actor }: { name: string; actor: BlackfenActor }) {
  const pct = Math.max(0, Math.min(100, (actor.hp / actor.max_hp) * 100));
  return <div className="mb-3"><div className="flex justify-between text-sm"><span>{name}</span><span>AC {actor.armor_class} | HP {actor.hp}/{actor.max_hp}</span></div><div className="mt-1 h-2 rounded bg-stone-800"><div className="h-2 rounded bg-emerald-400" style={{ width: `${pct}%` }} /></div></div>;
}

function letterLabel(index: number): string {
  return String.fromCharCode(65 + index);
}
