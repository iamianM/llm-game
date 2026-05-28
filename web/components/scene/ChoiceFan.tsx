"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useState } from "react";
import type { AvailableAction } from "../../lib/types";

type Props = {
  actions: AvailableAction[];
  locked: boolean;
  onChoose: (action: AvailableAction) => void;
};

const HINT_LABEL: Record<string, { label: string; tone: "good" | "bad" | "neutral" }> = {
  "+": { label: "Pulse +", tone: "good" },
  "-": { label: "Pulse -", tone: "bad" },
};

export function ChoiceFan({ actions, locked, onChoose }: Props) {
  const reduce = useReducedMotion();
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  if (!actions.length) return null;
  return (
    <motion.div
      data-testid="choice-fan"
      className={`choice-fan${actions.length > 4 ? " is-scroll" : ""}`}
      initial={reduce ? false : "hidden"}
      animate="show"
      variants={{
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: reduce ? 0 : 0.06 } },
      }}
      onClick={(event) => event.stopPropagation()}
    >
      {actions.map((action, index) => {
        const key = `${action.kind}-${action.target_id}-${action.intent_id}-${index}`;
        const hint = action.audience_hint ? HINT_LABEL[action.audience_hint] : null;
        return (
          <motion.button
            data-testid="choice"
            data-role="choice"
            data-action-kind={action.kind}
            key={key}
            type="button"
            aria-label={action.label}
            disabled={locked || selectedKey !== null}
            className={`choice-bubble${selectedKey === key ? " is-selected" : ""}`}
            variants={{
              hidden: { y: 12, opacity: 0, scale: 0.96 },
              show: { y: 0, opacity: 1, scale: 1 },
            }}
            transition={reduce ? { duration: 0.06 } : { duration: 0.18 }}
            onClick={() => {
              setSelectedKey(key);
              window.setTimeout(() => onChoose(action), reduce ? 40 : 180);
            }}
          >
            <span className="choice-text">{action.label}</span>
            <span className="choice-meta">
              {hint ? <i className={`hint hint-${hint.tone}`}>{hint.label}</i> : null}
              {action.risk ? <i>{action.risk}</i> : null}
              {action.stat_used ? <i>{action.stat_used}</i> : null}
            </span>
          </motion.button>
        );
      })}
      <style jsx global>{`
        .choice-fan {
          position: absolute;
          z-index: 10;
          left: 50%;
          bottom: clamp(82px, 13vh, 130px);
          width: min(720px, calc(100vw - 28px));
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 10px;
          transform: translateX(-50%);
          pointer-events: auto;
        }
        .choice-fan.is-scroll {
          max-height: min(30vh, 260px);
          overflow-y: auto;
          padding-right: 4px;
          mask-image: linear-gradient(180deg, transparent, #000 12px, #000 calc(100% - 18px), transparent);
        }
        .choice-bubble {
          position: relative;
          min-height: 58px;
          display: grid;
          align-content: center;
          gap: 5px;
          padding: 12px 15px;
          border-radius: 22px;
          border: 1px solid rgba(217,167,58,.42);
          background:
            linear-gradient(180deg, rgba(248,246,239,.98), rgba(238,226,201,.96)),
            radial-gradient(80% 80% at 10% 0, rgba(217,167,58,.18), transparent 65%);
          box-shadow: var(--shadow-md), var(--inset-gold);
          color: var(--ink);
          text-align: left;
          cursor: pointer;
          transition: transform .16s, box-shadow .16s, border-color .16s;
        }
        .choice-bubble:hover:not(:disabled) {
          transform: translateY(-3px);
          border-color: rgba(217,167,58,.75);
          box-shadow: var(--shadow-lg), 0 0 20px rgba(217,167,58,.25);
        }
        .choice-bubble.is-selected {
          transform: translateY(-8px) scale(.98);
          opacity: .82;
        }
        .choice-bubble:disabled {
          cursor: not-allowed;
        }
        .choice-text {
          font-family: var(--font-display);
          font-size: 17px;
          font-weight: 650;
          line-height: 1.22;
        }
        .choice-meta {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
          min-height: 0;
        }
        .choice-meta i {
          font-style: normal;
          font-size: 10px;
          font-weight: 700;
          letter-spacing: .1em;
          text-transform: uppercase;
          color: rgba(73,57,42,.7);
        }
        .hint-good { color: #316844 !important; }
        .hint-bad { color: var(--accent-deep) !important; }
        @media (max-width: 520px) {
          .choice-fan {
            bottom: 72px;
            grid-template-columns: 1fr;
            gap: 8px;
            width: min(342px, calc(100vw - 28px));
            max-height: min(34vh, 276px);
            overflow-y: auto;
          }
          .choice-bubble {
            min-height: 52px;
            padding: 10px 13px;
            border-radius: 19px;
          }
          .choice-text {
            font-size: 16px;
          }
        }
      `}</style>
    </motion.div>
  );
}
