import type { IslanderSummary } from "../../lib/types";
import { Avatar } from "../ui/Avatar";

const moodRing: Record<string, string> = {
  warm: "border-[var(--good-soft)] shadow-[0_0_44px_rgba(111,178,138,.35)]",
  flirty: "border-[var(--accent-soft)] shadow-[0_0_44px_rgba(185,80,47,.32)]",
  tense: "border-[var(--bad-soft)] shadow-[0_0_44px_rgba(201,92,74,.32)]",
  playful: "border-gold shadow-[0_0_44px_rgba(200,147,42,.32)]"
};

export function NpcPortrait({ npc }: { npc: IslanderSummary }) {
  const ring = moodRing[npc.mood] ?? "border-white/25 shadow-[0_0_44px_rgba(255,244,224,.18)]";
  return (
    <div className="grid justify-items-center gap-4">
      <div className={`rounded-full border-4 bg-black/20 p-3 ${ring}`}>
        <Avatar id={npc.id} name={npc.name} size="xl" />
      </div>
      <div className="rounded-full bg-black/35 px-4 py-2 font-display text-2xl">{npc.name}</div>
    </div>
  );
}
