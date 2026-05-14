"use client";

import { useEffect, useState } from "react";

import type { SessionState } from "../../lib/types";
import { CastGrid } from "./CastGrid";
import { CastPopout } from "./CastPopout";
import { CouplesPanel } from "./CouplesPanel";
import { MemoriesList } from "./MemoriesList";
import { VillaMap } from "./VillaMap";

type Props = { state: SessionState; open: boolean; sessionId: string; onClose: () => void };

export function RightRail({ state, open, sessionId, onClose }: Props) {
  const [activeProfile, setActiveProfile] = useState<string | null>(null);
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <>
      <aside className={`fixed right-0 top-0 z-40 h-screen w-80 border-l border-white/10 bg-[var(--bg-elev)] p-4 text-[var(--card)] shadow-[var(--shadow-stage)] transition ${open ? "translate-x-0" : "pointer-events-none translate-x-full"}`}>
        <button aria-label="Close right rail" onClick={onClose} className="mb-3 rounded px-3 py-2 text-sm hover:bg-white/10">Close</button>
        <div className="space-y-4 overflow-y-auto pb-12">
          <VillaMap snapshot={state.villa_snapshot} />
          <CouplesPanel couples={state.couples} />
          <CastGrid
            cast={state.islanders}
            onOpenProfile={(npcId) => {
              setActiveProfile(npcId);
              onClose();
            }}
          />
          <MemoriesList memories={state.player.memories} />
        </div>
      </aside>
      {activeProfile ? <CastPopout sessionId={sessionId} npcId={activeProfile} onClose={() => setActiveProfile(null)} /> : null}
    </>
  );
}
