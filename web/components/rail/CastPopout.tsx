"use client";

import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { getCast } from "../../lib/api";
import { RELATIONSHIP_BONDS, type ApiRelationship } from "../../lib/types";
import { Avatar } from "../ui/Avatar";

export function CastPopout({ sessionId, npcId, onClose }: { sessionId: string; npcId: string; onClose: () => void }) {
  const { data } = useQuery({ queryKey: ["cast", sessionId, npcId], queryFn: () => getCast(sessionId, npcId) });
  const closeRef = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="popout-root">
      <button className="popout-backdrop" aria-label="Close profile" onClick={onClose} />
      <div role="dialog" aria-modal="true" aria-labelledby="cast-title" className="popout-frame">
        <section className="popout-card">
          <header className="card-header">
            <div className="header-glow" aria-hidden />
            <div className="header-inner">
              <Avatar id={data?.id ?? "you"} name={data?.name ?? "?"} size="lg" />
              <div className="header-text">
                <p className="header-eyebrow">{data?.archetype ?? "—"} · at {data?.location ?? "—"}</p>
                <h2 id="cast-title" className="header-name">{data?.name ?? "…"}</h2>
              </div>
              <button ref={closeRef} onClick={onClose} aria-label="Close" className="header-close"><X size={18} /></button>
            </div>
          </header>

          <div className="card-body">
            {data ? (
              <>
                <p className="backstory">{data.backstory}</p>

                <div className="section">
                  <h3 className="section-title">Connection</h3>
                  <ConnectionPanel relationship={data.relationship} />
                </div>

                <div className="section">
                  <h3 className="section-title">Ideal Match</h3>
                  <dl className="top-grid">
                    {Object.entries(data.ideal_match).map(([key, value]) => (
                      <div key={key} className={`top-item ${value ? "is-revealed" : ""}`}>
                        <dt>{key.replaceAll("_", " ")}</dt>
                        <dd>{value ? String(value) : "???"}</dd>
                      </div>
                    ))}
                  </dl>
                </div>

                <div className="section discovery">
                  <h3 className="section-title gold">What you know</h3>
                  <KnownFacts facts={data.known_facts} />
                </div>

                <div className="section">
                  <h3 className="section-title">Recent memories</h3>
                  {data.memories.length ? data.memories.map((m, index) => (
                    <p
                      key={`${m.id}-${m.holder_id}-${m.subject_id}-${m.formed_on_turn}-${index}`}
                      className="memory"
                    >
                      {m.content}
                    </p>
                  )) : <p className="empty">No memories yet.</p>}
                </div>
              </>
            ) : <p className="empty">Loading…</p>}
          </div>
        </section>
      </div>

      <style jsx>{`
        .popout-root { position: relative; z-index: 50; }
        .popout-backdrop {
          position: fixed; inset: 0;
          background:
            radial-gradient(60% 50% at 50% 30%, rgba(212,99,62,.08), transparent 70%),
            rgba(4,3,2,.75);
          backdrop-filter: blur(10px);
          border: 0;
          cursor: pointer;
        }
        .popout-frame {
          position: fixed; inset: 0;
          display: grid;
          place-items: center;
          padding: 24px;
        }
        .popout-card {
          width: 100%;
          max-width: 560px;
          max-height: 86vh;
          overflow: hidden;
          border-radius: var(--r-2xl);
          background: linear-gradient(180deg, #1a130d 0%, #100a07 100%);
          border: 1px solid rgba(217,167,58,.4);
          box-shadow: var(--shadow-stage), 0 0 64px rgba(212,99,62,.12), var(--inset-gold);
          color: var(--ink-on-dark);
          display: grid;
          grid-template-rows: auto 1fr;
          animation: drift-up .35s cubic-bezier(.22,.61,.36,1) both;
        }

        .card-header {
          position: relative;
          padding: 22px 24px;
          background:
            linear-gradient(180deg, rgba(212,99,62,.18), rgba(0,0,0,.0)),
            radial-gradient(80% 60% at 30% 0%, rgba(217,167,58,.18), transparent 60%);
          border-bottom: 1px solid rgba(217,167,58,.25);
          overflow: hidden;
        }
        .header-glow {
          position: absolute; left: 0; right: 0; top: -40%;
          height: 100%;
          background: radial-gradient(50% 60% at 50% 50%, rgba(217,167,58,.18), transparent 70%);
          filter: blur(20px);
          pointer-events: none;
        }
        .header-inner {
          position: relative;
          display: grid;
          grid-template-columns: auto 1fr auto;
          align-items: center;
          gap: 14px;
        }
        .header-eyebrow {
          font-size: 11px;
          font-weight: 700;
          letter-spacing: .14em;
          text-transform: uppercase;
          color: var(--gold-soft);
          opacity: .85;
        }
        .header-name {
          margin: 4px 0 0;
          font-family: var(--font-display);
          font-size: 32px;
          font-weight: 600;
          color: var(--card);
          letter-spacing: -.01em;
        }
        .header-close {
          display: grid;
          place-items: center;
          width: 32px; height: 32px;
          border: 1px solid rgba(217,167,58,.35);
          border-radius: var(--r-md);
          background: rgba(8,6,4,.4);
          color: var(--gold-soft);
          cursor: pointer;
          transition: background .15s, color .15s;
        }
        .header-close:hover { background: rgba(217,167,58,.18); color: var(--card); }

        .card-body {
          overflow-y: auto;
          padding: 20px 24px 26px;
          display: grid;
          gap: 20px;
        }
        .backstory {
          margin: 0;
          font-size: 14px;
          line-height: 1.65;
          color: var(--muted-on-dark);
          font-style: italic;
        }

        .section {
          padding: 16px 18px;
          border-radius: var(--r-lg);
          background: rgba(248,236,210,.04);
          border: 1px solid rgba(248,236,210,.08);
        }
        .section-title {
          margin: 0 0 12px;
          font-family: var(--font-display);
          font-size: 13px;
          font-weight: 700;
          letter-spacing: .14em;
          text-transform: uppercase;
          color: var(--muted-on-dark);
        }
        .section-title.gold { color: var(--gold-soft); }

        .top-grid { display: grid; gap: 8px; margin: 0; }
        .top-item {
          display: grid;
          grid-template-columns: 130px 1fr;
          gap: 12px;
          font-size: 13px;
          padding: 4px 0;
          border-bottom: 1px dashed rgba(248,236,210,.08);
        }
        .top-item:last-child { border-bottom: 0; }
        .top-item dt {
          text-transform: capitalize;
          color: var(--muted-on-dark);
          letter-spacing: .03em;
        }
        .top-item dd {
          margin: 0;
          color: var(--muted-on-dark);
          font-style: italic;
        }
        .top-item.is-revealed dd {
          color: var(--card);
          font-style: normal;
        }

        .discovery {
          background:
            linear-gradient(180deg, rgba(217,167,58,.08), rgba(217,167,58,.02)),
            rgba(8,6,4,.55);
          border: 1px solid rgba(217,167,58,.28);
          position: relative;
        }
        .discovery::before {
          content: "";
          position: absolute; left: 0; right: 0; top: 0;
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(217,167,58,.6), transparent);
        }

        .memory {
          margin: 8px 0 0;
          font-size: 13px;
          line-height: 1.55;
          color: var(--muted-on-dark);
          padding-left: 12px;
          border-left: 2px solid rgba(217,167,58,.25);
          font-style: italic;
        }
        .empty {
          font-size: 13px;
          color: var(--muted-on-dark);
          opacity: .7;
          margin: 0;
        }
      `}</style>
    </div>
  );
}

const BOND_LABELS: Record<string, string> = {
  chemistry: "Chemistry",
  affection: "Affection",
  trust: "Trust",
  friendship: "Friendship",
};

// The composite Connection read: a single legible score + tier word up top, with
// the four raw bonds demoted to a "what's underneath" breakdown. The ring is an
// SVG donut whose arc fills proportionally to the 0-100 score.
function ConnectionPanel({ relationship }: { relationship: ApiRelationship }) {
  const score = Math.max(0, Math.min(100, relationship.connection));
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const dash = (score / 100) * circumference;
  return (
    <div className="conn">
      <div className="conn-ring">
        <svg viewBox="0 0 100 100" className="ring-svg" role="img" aria-label={`Connection ${score} of 100, ${relationship.connection_label}`}>
          <circle className="ring-bg" cx="50" cy="50" r={radius} />
          <circle
            className="ring-fill"
            cx="50"
            cy="50"
            r={radius}
            strokeDasharray={`${dash} ${circumference - dash}`}
          />
        </svg>
        <div className="ring-center">
          <span className="ring-score">{score}</span>
        </div>
      </div>
      <div className="conn-meta">
        <span className="conn-tier">{relationship.connection_label}</span>
        <div className="conn-breakdown">
          {RELATIONSHIP_BONDS.map((bond) => {
            const value = Math.max(0, Math.min(100, relationship[bond]));
            return (
              <div key={bond} className="bd-row">
                <span className="bd-label">{BOND_LABELS[bond] ?? bond}</span>
                <div className="bd-track"><span className="bd-fill" style={{ width: `${value}%` }} /></div>
              </div>
            );
          })}
        </div>
      </div>

      <style jsx>{`
        .conn {
          display: grid;
          grid-template-columns: auto 1fr;
          align-items: center;
          gap: 18px;
        }
        .conn-ring { position: relative; width: 96px; height: 96px; flex: 0 0 auto; }
        .ring-svg { width: 100%; height: 100%; transform: rotate(-90deg); }
        .ring-bg {
          fill: none;
          stroke: rgba(248,236,210,.1);
          stroke-width: 9;
        }
        .ring-fill {
          fill: none;
          stroke: var(--accent);
          stroke-width: 9;
          stroke-linecap: round;
          filter: drop-shadow(0 0 6px var(--accent-glow));
          transition: stroke-dasharray .6s cubic-bezier(.22,.61,.36,1);
        }
        .ring-center {
          position: absolute; inset: 0;
          display: grid;
          place-items: center;
        }
        .ring-score {
          font-family: var(--font-display);
          font-size: 30px;
          font-weight: 700;
          color: var(--card);
          font-variant-numeric: tabular-nums;
          line-height: 1;
        }
        .conn-meta { display: grid; gap: 10px; min-width: 0; }
        .conn-tier {
          font-family: var(--font-display);
          font-size: 18px;
          font-weight: 600;
          color: var(--gold-soft);
          letter-spacing: .01em;
        }
        .conn-breakdown { display: grid; gap: 7px; }
        .bd-row {
          display: grid;
          grid-template-columns: 78px 1fr;
          align-items: center;
          gap: 10px;
        }
        .bd-label {
          font-size: 11px;
          letter-spacing: .04em;
          color: var(--muted-on-dark);
        }
        .bd-track {
          height: 6px;
          border-radius: var(--r-pill);
          background: rgba(248,236,210,.08);
          overflow: hidden;
        }
        .bd-fill {
          display: block;
          height: 100%;
          background: linear-gradient(90deg, var(--accent-deep), var(--accent), var(--accent-soft));
          border-radius: var(--r-pill);
        }
        @media (max-width: 420px) {
          .conn { grid-template-columns: 1fr; justify-items: center; text-align: center; }
          .conn-meta { width: 100%; }
          .bd-label { text-align: left; }
        }
      `}</style>
    </div>
  );
}

function KnownFacts({ facts }: { facts: NonNullable<Awaited<ReturnType<typeof getCast>>>["known_facts"] }) {
  if (!facts.length) return <p className="empty">Nothing confirmed yet. Spark with them to learn more.<style jsx>{`.empty { font-size: 13px; color: var(--muted-on-dark); opacity: .7; }`}</style></p>;
  const groups = [
    ["confirmed", "Confirmed", "good"],
    ["heard", "Heard around", "warn"],
    ["trivia", "Trivia", "gold"]
  ] as const;
  return (
    <div className="kn-groups">
      {groups.map(([group, label, tone]) => {
        const items = facts.filter((fact) => fact.group === group);
        if (!items.length) return null;
        return (
          <div key={group} className={`kn-group kn-${tone}`}>
            <p className="kn-label">{label} · {items.length}</p>
            {items.map((fact) => (
              <div key={fact.fact_key} className="kn-fact">
                <div className="kn-fact-head">
                  <span className="kn-fact-label">{fact.label}</span>
                  <span className="kn-conf">{Math.round(fact.confidence * 100)}%</span>
                </div>
                <p className="kn-value">{fact.value}</p>
                <p className="kn-citation">{fact.citation}</p>
              </div>
            ))}
          </div>
        );
      })}
      <style jsx>{`
        .kn-groups { display: grid; gap: 12px; }
        .kn-group {
          padding: 12px 14px;
          border-radius: var(--r-md);
          border: 1px solid;
        }
        .kn-good {
          border-color: rgba(164,205,177,.28);
          background: rgba(45,106,63,.06);
        }
        .kn-warn {
          border-color: rgba(244,227,184,.28);
          background: rgba(168,122,31,.06);
        }
        .kn-gold {
          border-color: rgba(217,167,58,.28);
          background: rgba(217,167,58,.04);
        }
        .kn-label {
          margin: 0 0 8px;
          font-size: 10px;
          letter-spacing: .16em;
          text-transform: uppercase;
          font-weight: 700;
          color: var(--gold-soft);
        }
        .kn-fact { padding: 6px 0; border-top: 1px dashed rgba(248,236,210,.08); }
        .kn-fact:first-of-type { border-top: 0; padding-top: 0; }
        .kn-fact-head {
          display: flex; justify-content: space-between; align-items: baseline;
          font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
        }
        .kn-fact-label { color: var(--muted-on-dark); }
        .kn-conf { font-weight: 700; color: var(--gold-soft); font-variant-numeric: tabular-nums; }
        .kn-value {
          margin: 4px 0 4px;
          font-family: var(--font-display);
          font-size: 14.5px;
          line-height: 1.45;
          color: var(--card);
        }
        .kn-citation {
          margin: 0;
          font-size: 11px;
          color: var(--muted-on-dark);
          opacity: .7;
          font-style: italic;
        }
      `}</style>
    </div>
  );
}
