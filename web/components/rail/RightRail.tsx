"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";

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
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <>
      <aside className={`rail ${open ? "is-open" : ""}`}>
        <header className="rail-head">
          <p className="rail-eyebrow">Field Report</p>
          <button aria-label="Close right rail" onClick={onClose} className="rail-close"><X size={16} /></button>
        </header>
        <div className="rail-body">
          <VillaMap snapshot={state.villa_snapshot} />
          <CouplesPanel couples={state.couples} />
          <CastGrid
            cast={state.islanders}
            onOpenProfile={(npcId) => { setActiveProfile(npcId); onClose(); }}
          />
          <MemoriesList memories={state.player.memories} />
        </div>
      </aside>
      {activeProfile ? <CastPopout sessionId={sessionId} npcId={activeProfile} onClose={() => setActiveProfile(null)} /> : null}

      <style jsx>{`
        .rail {
          position: fixed;
          right: 0; top: 0;
          z-index: 40;
          height: 100vh;
          width: 340px;
          padding: 0;
          background: linear-gradient(180deg, #1a130d 0%, #0c0805 100%);
          border-left: 1px solid rgba(217,167,58,.28);
          box-shadow: var(--shadow-stage);
          color: var(--ink-on-dark);
          transform: translateX(100%);
          transition: transform .35s cubic-bezier(.22,.61,.36,1);
          display: grid;
          grid-template-rows: auto 1fr;
        }
        .rail.is-open { transform: translateX(0); }
        .rail-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 18px 20px 14px;
          border-bottom: 1px solid rgba(217,167,58,.18);
          background: rgba(212,99,62,.05);
        }
        .rail-eyebrow {
          margin: 0;
          font-family: var(--font-display);
          font-style: italic;
          font-size: 16px;
          color: var(--gold-soft);
          letter-spacing: .04em;
        }
        .rail-close {
          display: grid;
          place-items: center;
          width: 28px; height: 28px;
          border-radius: var(--r-md);
          border: 1px solid rgba(217,167,58,.3);
          background: rgba(8,6,4,.5);
          color: var(--gold-soft);
          cursor: pointer;
          transition: background .15s, color .15s;
        }
        .rail-close:hover { background: rgba(217,167,58,.2); color: var(--card); }
        .rail-body {
          padding: 16px 16px 60px;
          overflow-y: auto;
          display: grid;
          gap: 14px;
        }
      `}</style>
    </>
  );
}
