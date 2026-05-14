import { PanelRightOpen, Settings } from "lucide-react";
import type { SessionState } from "../../lib/types";
import { PulseMeter } from "./PulseMeter";
import { Pill } from "../ui/Pill";

type Props = { state: SessionState; onRail: () => void; onSettings: () => void };

export function TopBar({ state, onRail, onSettings }: Props) {
  return (
    <header className="flex h-14 items-center gap-4 border-b border-white/10 bg-black/25 px-4 backdrop-blur">
      <button aria-label="Open right rail" onClick={onRail} className="rounded p-2 hover:bg-white/10"><PanelRightOpen size={20} /></button>
      <div className="font-display text-lg text-[var(--card)]">Paradise Hearts</div>
      <div className="ml-auto flex items-center gap-2">
        <Pill tone="gold">Day {state.day}</Pill>
        <Pill>{state.phase_label}</Pill>
        <Pill>T{state.turn_index}</Pill>
        <Pill>{clockText(state.phase_clock)}</Pill>
        <PulseMeter score={state.audience.public_perception} delta={state.audience.recent_delta} />
        <button aria-label="Open settings" onClick={onSettings} className="rounded p-2 hover:bg-white/10"><Settings size={20} /></button>
      </div>
    </header>
  );
}

function clockText(clock: Record<string, unknown>) {
  const phase = String(clock.phase ?? "");
  const elapsed = Number(clock.elapsed_minutes ?? 0);
  const anchors: Record<string, number> = {
    morning: 9 * 60,
    intros: 10 * 60 + 30,
    challenge: 12 * 60 + 30,
    afternoon: 14 * 60,
    text: 17 * 60,
    evening: 19 * 60 + 30,
    complete: 22 * 60
  };
  const total = (anchors[phase] ?? 9 * 60) + elapsed;
  const hours = Math.floor(total / 60) % 24;
  const minutes = total % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}
