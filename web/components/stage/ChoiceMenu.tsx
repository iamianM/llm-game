"use client";

import type { AvailableAction } from "../../lib/types";

type Props = { actions: AvailableAction[]; locked: boolean; onChoose: (action: AvailableAction) => void };

const HINT_LABEL: Record<string, { label: string; tone: "good" | "bad" | "neutral" }> = {
  "+": { label: "Audience +", tone: "good" },
  "-": { label: "Audience −", tone: "bad" }
};

const RISK_TONE: Record<string, string> = {
  low: "low",
  medium: "med",
  med: "med",
  high: "high"
};

export function ChoiceMenu({ actions, locked, onChoose }: Props) {
  if (!actions.length) return null;
  return (
    <div data-testid="choice-menu" className="choice-stage">
      <div className="choice-row">
        {actions.slice(0, 5).map((action, index) => {
          const hint = action.audience_hint ? HINT_LABEL[action.audience_hint] : null;
          const risk = action.risk ? RISK_TONE[action.risk.toLowerCase()] : null;
          return (
            <button
              data-role="choice"
              data-testid="choice"
              disabled={locked}
              key={`${action.kind}-${action.target_id}-${action.intent_id}-${index}`}
              onClick={() => onChoose(action)}
              className="choice-card"
            >
              <span className="choice-corner" aria-hidden />
              <div className="choice-top">
                {hint ? (
                  <span className={`hint hint-${hint.tone}`}>{hint.label}</span>
                ) : <span className="hint hint-neutral">·</span>}
                {risk ? <span className={`risk risk-${risk}`}>{action.risk}</span> : null}
              </div>
              <div className="choice-label">{action.label}</div>
              {action.stat_used ? <div className="choice-stat">uses · {action.stat_used}</div> : null}
            </button>
          );
        })}
      </div>

      <style jsx>{`
        .choice-stage {
          background: linear-gradient(180deg, rgba(8,6,4,.95), rgba(8,6,4,1));
          padding: 14px 18px 22px;
          border-top: 1px solid rgba(217,167,58,.12);
        }
        .choice-row {
          max-width: 1080px;
          margin: 0 auto;
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          gap: 12px;
        }
        @media (max-width: 1024px) {
          .choice-row { grid-template-columns: repeat(3, 1fr); gap: 8px; }
        }
        @media (max-width: 700px) {
          .choice-row { grid-template-columns: repeat(2, 1fr); gap: 8px; }
        }
        @media (max-width: 480px) {
          .choice-row { grid-template-columns: 1fr 1fr; gap: 6px; }
          .choice-stage { padding: 10px 10px 14px; }
        }
        .choice-card {
          position: relative;
          display: grid;
          gap: 10px;
          padding: 12px 14px 14px;
          min-height: 110px;
          border-radius: var(--r-lg);
          background:
            linear-gradient(180deg, rgba(248,246,239,.04), rgba(248,246,239,.01)),
            rgba(20,16,12,.7);
          border: 1px solid rgba(248,236,210,.14);
          color: var(--ink-on-dark);
          cursor: pointer;
          text-align: left;
          transition: transform .18s cubic-bezier(.22,.61,.36,1), box-shadow .18s, border-color .18s, background .18s;
          overflow: hidden;
          font-family: var(--font-body);
        }
        .choice-card::before {
          content: "";
          position: absolute;
          inset: 0;
          border-radius: inherit;
          padding: 1px;
          background: linear-gradient(140deg, rgba(217,167,58,.0), rgba(217,167,58,.18) 50%, rgba(217,167,58,.0));
          -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
          mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
          -webkit-mask-composite: xor;
          mask-composite: exclude;
          pointer-events: none;
          opacity: 0;
          transition: opacity .18s;
        }
        .choice-card:hover:not(:disabled) {
          transform: translateY(-3px);
          background:
            linear-gradient(180deg, rgba(248,246,239,.07), rgba(248,246,239,.02)),
            rgba(28,22,16,.85);
          border-color: rgba(217,167,58,.55);
          box-shadow: var(--shadow-lg), 0 0 22px rgba(217,167,58,.15);
        }
        .choice-card:hover:not(:disabled)::before { opacity: 1; }
        .choice-card:disabled { opacity: .45; cursor: not-allowed; }
        .choice-corner {
          position: absolute;
          left: -1px; bottom: -1px;
          width: 14px; height: 14px;
          border-left: 1px solid rgba(217,167,58,.55);
          border-bottom: 1px solid rgba(217,167,58,.55);
          border-bottom-left-radius: var(--r-lg);
          opacity: 0;
          transition: opacity .18s;
        }
        .choice-card:hover .choice-corner { opacity: 1; }

        .choice-top {
          display: flex;
          align-items: center;
          gap: 6px;
          min-height: 18px;
        }
        .hint {
          display: inline-flex;
          align-items: center;
          padding: 2px 8px;
          font-size: 10px;
          font-weight: 700;
          letter-spacing: .1em;
          text-transform: uppercase;
          border-radius: var(--r-pill);
          border: 1px solid;
        }
        .hint-good { color: var(--good-soft); border-color: rgba(164,205,177,.5); background: rgba(45,106,63,.18); }
        .hint-bad { color: var(--bad-soft); border-color: rgba(247,226,221,.45); background: rgba(193,75,58,.18); }
        .hint-neutral { color: rgba(181,161,135,.55); border-color: rgba(248,236,210,.12); background: transparent; padding: 2px 9px; }

        .risk {
          font-size: 10px;
          letter-spacing: .14em;
          text-transform: uppercase;
          color: var(--muted-on-dark);
          opacity: .85;
          padding: 2px 6px;
          border-radius: var(--r-sm);
          border: 1px solid rgba(248,236,210,.12);
        }
        .risk-low { color: var(--good-soft); border-color: rgba(164,205,177,.35); }
        .risk-med { color: var(--gold-soft); border-color: rgba(244,227,184,.45); }
        .risk-high { color: var(--bad-soft); border-color: rgba(247,226,221,.45); }

        .choice-label {
          font-family: var(--font-display);
          font-size: 16px;
          font-weight: 500;
          line-height: 1.3;
          color: var(--ink-on-dark);
        }
        .choice-stat {
          font-size: 11px;
          color: var(--muted-on-dark);
          opacity: .75;
          letter-spacing: .04em;
        }
      `}</style>
    </div>
  );
}
