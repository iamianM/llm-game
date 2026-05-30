"use client";

import { PanelRightOpen, Settings, Shirt, Clock } from "lucide-react";
import type { SessionState } from "../../lib/types";
import { PulseMeter } from "./PulseMeter";

type Props = { state: SessionState; onRail: () => void; onSettings: () => void; onWardrobe: () => void };

export function TopBar({ state, onRail, onSettings, onWardrobe }: Props) {
  return (
    <header className="topbar">
      <button aria-label="Open right rail" onClick={onRail} className="icon-btn"><PanelRightOpen size={18} /></button>
      <div className="brand">
        <span className="brand-dot" />
        <span className="brand-text">Paradise Hearts</span>
      </div>

      <div className="hud-row">
        <span className="day-chip" aria-label={`Day ${state.day}`}>
          <span className="day-label">Day</span>
          <span className="day-num">{state.day}</span>
        </span>
        <span className="divider" aria-hidden />
        <span className="phase-chip">{state.phase_label}</span>
        <span className="turn-chip"><Clock size={11} /> {clockText(state.phase_clock)}</span>
      </div>

      <div className="hud-right">
        <PulseMeter score={state.audience.public_perception} delta={state.audience.recent_delta} />
        <button aria-label="Open wardrobe" onClick={onWardrobe} className="icon-btn"><Shirt size={18} /></button>
        <button aria-label="Open settings" onClick={onSettings} className="icon-btn"><Settings size={18} /></button>
      </div>

      <style jsx>{`
        .topbar {
          display: flex;
          align-items: center;
          gap: 14px;
          height: 56px;
          padding: 0 14px;
          background:
            linear-gradient(180deg, rgba(20,16,12,.95), rgba(8,6,4,.85)),
            linear-gradient(90deg, transparent, rgba(217,167,58,.06), transparent);
          border-bottom: 1px solid rgba(217,167,58,.18);
          backdrop-filter: blur(10px);
          position: relative;
          z-index: 6;
        }
        .topbar::after {
          content: "";
          position: absolute;
          left: 0; right: 0; bottom: -1px;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(217,167,58,.4), transparent);
        }
        .icon-btn {
          display: grid;
          place-items: center;
          width: 32px; height: 32px;
          border-radius: var(--r-md);
          color: var(--ink-on-dark);
          background: transparent;
          border: 0;
          cursor: pointer;
          transition: background .15s, color .15s;
        }
        .icon-btn:hover { background: rgba(255,255,255,.08); color: var(--gold-soft); }

        .brand {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding-right: 14px;
          border-right: 1px solid rgba(248,236,210,.1);
        }
        .brand-dot {
          width: 8px; height: 8px;
          border-radius: 50%;
          background: var(--accent);
          box-shadow: 0 0 12px var(--accent-glow);
          animation: ambient-pulse 3s ease-in-out infinite;
        }
        .brand-text {
          font-family: var(--font-display);
          font-size: 15px;
          color: var(--ink-on-dark);
          letter-spacing: .02em;
        }

        .hud-row {
          display: inline-flex;
          align-items: center;
          gap: 10px;
        }
        .day-chip {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 4px 12px;
          border-radius: var(--r-pill);
          background: linear-gradient(180deg, rgba(217,167,58,.18), rgba(168,122,31,.12));
          border: 1px solid rgba(217,167,58,.4);
          color: var(--gold-soft);
        }
        .day-label {
          font-size: 10px;
          letter-spacing: .14em;
          text-transform: uppercase;
          font-weight: 700;
          opacity: .9;
        }
        .day-num {
          font-family: var(--font-display);
          font-size: 16px;
          font-weight: 700;
          color: var(--card);
        }
        .divider { width: 1px; height: 16px; background: rgba(248,236,210,.12); }
        .phase-chip {
          font-family: var(--font-display);
          font-style: italic;
          font-size: 14px;
          color: var(--ink-on-dark);
          letter-spacing: .02em;
        }
        .turn-chip {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          font-size: 11px;
          font-variant-numeric: tabular-nums;
          color: var(--muted-on-dark);
          letter-spacing: .04em;
          white-space: nowrap;
        }

        .hud-right {
          margin-left: auto;
          display: inline-flex;
          align-items: center;
          gap: 12px;
        }

        /* Responsive overrides MUST come after the base rules above: media
           queries and base selectors share specificity, so a later base rule
           would otherwise win over an earlier @media one (which previously left
           the clock visible and the phase font un-shrunk on phones). */
        @media (max-width: 700px) {
          .topbar { gap: 7px; padding: 0 8px; }
          .icon-btn { width: 30px; height: 30px; flex: 0 0 auto; }
          .brand { padding-right: 4px; border-right: 0; }
          .brand-text { display: none; }
          .turn-chip { display: none; }
          .phase-chip {
            font-size: 12px;
            max-width: min(38vw, 116px);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          .hud-row { gap: 6px; min-width: 0; }
          .day-chip { gap: 4px; padding: 4px 9px; }
          .divider { display: none; }
          .hud-right { gap: 6px; min-width: 0; }
        }
        @media (max-width: 420px) {
          .phase-chip { max-width: min(34vw, 92px); }
        }
      `}</style>
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
  const hours24 = Math.floor(total / 60) % 24;
  const minutes = total % 60;
  const period = hours24 >= 12 ? "PM" : "AM";
  const hours12 = hours24 % 12 === 0 ? 12 : hours24 % 12;
  return `${hours12}:${String(minutes).padStart(2, "0")} ${period}`;
}
