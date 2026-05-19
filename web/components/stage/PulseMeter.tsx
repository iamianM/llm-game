"use client";

type Props = { score: number; delta?: number | null };

export function PulseMeter({ score, delta }: Props) {
  const pct = Math.max(0, Math.min(100, score));
  const tone = pct >= 70 ? "good" : pct >= 40 ? "warm" : "low";
  return (
    <div className={`pulse pulse-${tone}`} aria-label={`Audience Pulse ${pct} of 100`}>
      <span className="pulse-label">Pulse</span>
      <div className="pulse-bar">
        <span className="pulse-fill" style={{ width: `${pct}%` }} />
        <span className="pulse-glint" />
      </div>
      <span className="pulse-num">{pct}</span>
      {typeof delta === "number" && delta !== 0 ? (
        <span className={`pulse-delta ${delta > 0 ? "up" : "down"}`}>{delta > 0 ? `+${delta}` : delta}</span>
      ) : null}
      <style jsx>{`
        .pulse {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 4px 12px 4px 10px;
          border-radius: var(--r-pill);
          background: rgba(8,6,4,.6);
          border: 1px solid rgba(217,167,58,.35);
          font-size: 12px;
          font-weight: 600;
          letter-spacing: .08em;
          text-transform: uppercase;
          color: var(--gold-soft);
        }
        .pulse-label { font-size: 10px; opacity: .85; }
        .pulse-bar {
          position: relative;
          width: 90px;
          height: 8px;
          border-radius: var(--r-pill);
          background: rgba(248,236,210,.08);
          overflow: hidden;
        }
        .pulse-fill {
          position: absolute;
          inset: 0;
          background: linear-gradient(90deg, var(--gold-deep), var(--gold), var(--gold-soft));
          border-radius: var(--r-pill);
          transition: width .6s cubic-bezier(.22,.61,.36,1);
          box-shadow: 0 0 12px var(--gold-glow);
        }
        .pulse-good .pulse-fill { background: linear-gradient(90deg, var(--gold-deep), var(--gold), #f3da7a); }
        .pulse-low .pulse-fill { background: linear-gradient(90deg, #6a3225, var(--accent), #d4633e); box-shadow: 0 0 12px var(--accent-glow); }
        .pulse-glint {
          position: absolute; inset: 0;
          background: linear-gradient(110deg, transparent 25%, rgba(255,255,255,.45) 50%, transparent 75%);
          background-size: 220% 100%;
          animation: shimmer 5s linear infinite;
          opacity: .5;
          pointer-events: none;
        }
        .pulse-num {
          font-family: var(--font-display);
          font-size: 14px;
          font-weight: 700;
          color: var(--card);
          letter-spacing: 0;
          text-transform: none;
        }
        .pulse-delta {
          font-size: 11px;
          font-weight: 700;
          padding: 1px 6px;
          border-radius: var(--r-pill);
          letter-spacing: 0;
          animation: drift-up .6s cubic-bezier(.22,.61,.36,1) both;
        }
        .pulse-delta.up { background: rgba(45,106,63,.3); color: var(--good-soft); border: 1px solid rgba(164,205,177,.4); }
        .pulse-delta.down { background: rgba(193,75,58,.3); color: var(--bad-soft); border: 1px solid rgba(247,226,221,.4); }
      `}</style>
    </div>
  );
}
