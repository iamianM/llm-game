import type { IslanderSummary } from "../../lib/types";
import { Avatar } from "../ui/Avatar";

export function CastGrid({ cast, onOpenProfile }: { cast: IslanderSummary[]; onOpenProfile: (npcId: string) => void }) {
  return (
    <section className="rounded-[var(--r-md)] border border-white/10 bg-white/5 p-3">
      <h3 className="font-display text-lg">Cast</h3>
      <div className="mt-3 grid grid-cols-4 gap-2">
        {cast.map((npc) => (
          <button key={npc.id} aria-label={`Open ${npc.name} profile`} onClick={() => onOpenProfile(npc.id)} className="grid justify-items-center gap-1 rounded p-2 hover:bg-white/10">
            <Avatar id={npc.id} name={npc.name} size="sm" />
            <span className="text-xs">{npc.name}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
