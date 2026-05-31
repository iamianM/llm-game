"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useState } from "react";
import type { AvailableAction } from "../../lib/types";
import { CATEGORY_SHORT, categoryFor, type IntentCategory } from "../../lib/scene/intents";

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
      className={`choice-fan${actions.length > 4 ? " is-scroll" : ""}${actions.length === 1 ? " is-single" : ""}${actions.length === 4 ? " is-quad" : ""}`}
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
            data-action-target={action.target_id ?? undefined}
            key={key}
            type="button"
            aria-label={displayLabel(action.label)}
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
            <span className="choice-text">{displayLabel(action.label)}</span>
            <span className="choice-meta">
              {categoryChip(action)}
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
          bottom: calc(clamp(14px, 3vh, 28px) + env(safe-area-inset-bottom, 0px));
          width: min(880px, calc(100vw - 24px));
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 8px;
          transform: translateX(-50%);
          pointer-events: auto;
        }
        .choice-fan.is-scroll {
          max-height: min(30vh, 260px);
          overflow-y: auto;
          padding-right: 4px;
          mask-image: linear-gradient(180deg, transparent, #000 12px, #000 calc(100% - 18px), transparent);
        }
        /* A lone CTA (e.g. "Join everyone at Firepit", "Continue") shouldn't
           stretch into a near-empty full-width bar — center a tidy pill. */
        .choice-fan.is-single {
          grid-template-columns: minmax(0, 340px);
          justify-content: center;
        }
        .choice-fan.is-single .choice-bubble {
          text-align: center;
          justify-items: center;
        }
        .choice-fan.is-single .choice-meta { justify-content: center; }
        /* Four options (the recoupling pick) read as a balanced, centered 2x2
           block instead of an auto-fit "3 + 1 orphan" on wide screens. */
        .choice-fan.is-quad {
          grid-template-columns: repeat(2, minmax(0, 260px));
          justify-content: center;
        }
        .choice-bubble {
          position: relative;
          min-height: 48px;
          display: grid;
          align-content: center;
          gap: 4px;
          padding: 9px 13px 10px;
          border-radius: 18px;
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
          font-size: 15px;
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
            bottom: calc(12px + env(safe-area-inset-bottom, 0px));
            grid-template-columns: 1fr 1fr;
            gap: 6px;
            width: calc(100vw - 16px);
            max-height: min(38vh, 320px);
            overflow-y: auto;
          }
          .choice-bubble {
            min-height: 42px;
            padding: 7px 10px 8px;
            border-radius: 14px;
          }
          .choice-text {
            font-size: 13px;
            line-height: 1.18;
          }
          .choice-meta i { font-size: 9px; }
        }
        .choice-chip {
          font-style: normal !important;
          font-size: 10px !important;
          font-weight: 700;
          letter-spacing: .08em;
          padding: 1px 7px 2px !important;
          border-radius: var(--r-pill);
          color: rgba(73,57,42,.85) !important;
        }
        .choice-chip.cat-friendly { background: rgba(212,168,122,.35); }
        .choice-chip.cat-flirty   { background: rgba(212,99,62,.32); color: var(--accent-deep) !important; }
        .choice-chip.cat-deep     { background: rgba(193,154,79,.42); color: rgba(60,42,18,.9) !important; }
        .choice-chip.cat-banter   { background: rgba(138,165,128,.38); color: rgba(46,68,40,.92) !important; }
      `}</style>
    </motion.div>
  );
}

// Option labels arrive from the engine with inconsistent casing — proper nouns
// ("Grand Designs", "Stay by Rihanna") are capitalized but generic answers come
// through lowercase ("audience favourite", "the unsent letter..."). As a button
// each should read as a proper option, so capitalize the leading letter for
// display only (engine state, feedback lines, and analytics keep the raw label).
function displayLabel(label: string): string {
  if (!label) return label;
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function categoryChip(action: AvailableAction) {
  // Only show chips when the action is a conversation-style turn — minigame
  // answers, recoupling picks, and ceremony joins shouldn't get a category tag.
  const conversational = new Set([
    "introduce_to",
    "start_conversation",
    "respond_with",
  ]);
  if (!conversational.has(action.kind)) return null;
  const category: IntentCategory = categoryFor(action.intent_id);
  return <i className={`choice-chip cat-${category}`}>{CATEGORY_SHORT[category]}</i>;
}
