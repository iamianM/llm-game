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
      className={`choice-fan${actions.length > 4 ? " is-scroll" : ""}${actions.length === 1 ? " is-single" : ""}`}
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
        /* Love Island mobile framing: the player's options stack as dark,
           translucent, full-width rounded buttons pinned to the bottom. */
        .choice-fan {
          position: absolute;
          z-index: 10;
          /* Reserve the bottom-left column for the player standee so the option
             bars sit to their right and never cover "you" (desktop/tablet). On
             mobile this is overridden to full-width — there the player lifts up
             out of the way instead. */
          left: calc(28vw + 40px);
          right: clamp(16px, 4vw, 64px);
          bottom: calc(clamp(14px, 3vh, 28px) + env(safe-area-inset-bottom, 0px));
          max-width: 560px;
          margin-inline: auto;
          display: grid;
          grid-template-columns: minmax(0, 1fr);
          gap: 8px;
          pointer-events: auto;
        }
        .choice-fan.is-scroll {
          max-height: min(34vh, 300px);
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
        .choice-bubble {
          position: relative;
          min-height: 50px;
          display: grid;
          align-content: center;
          gap: 4px;
          padding: 10px 16px 11px;
          border-radius: 16px;
          border: 1px solid rgba(217,167,58,.34);
          background: rgba(14,10,8,.6);
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
          box-shadow: 0 8px 22px rgba(0,0,0,.34);
          color: var(--ink-on-dark);
          text-align: left;
          cursor: pointer;
          transition: transform .16s, box-shadow .16s, border-color .16s, background .16s;
        }
        .choice-bubble:hover:not(:disabled) {
          transform: translateY(-2px);
          background: rgba(28,20,14,.72);
          border-color: rgba(217,167,58,.7);
          box-shadow: 0 10px 26px rgba(0,0,0,.4), 0 0 18px rgba(217,167,58,.22);
        }
        .choice-bubble.is-selected {
          transform: translateY(-4px) scale(.99);
          border-color: rgba(217,167,58,.85);
          background: rgba(40,28,18,.78);
        }
        .choice-bubble:disabled {
          cursor: not-allowed;
        }
        .choice-text {
          font-family: var(--font-display);
          font-size: 15.5px;
          font-weight: 650;
          line-height: 1.24;
          color: var(--card);
          text-shadow: 0 1px 6px rgba(0,0,0,.5);
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
          color: rgba(243,228,200,.6);
        }
        .hint-good { color: #7fd0a0 !important; }
        .hint-bad { color: #e6a86a !important; }
        @media (max-width: 520px) {
          .choice-fan {
            left: 8px;
            right: 8px;
            max-width: none;
            margin-inline: 0;
            bottom: calc(12px + env(safe-area-inset-bottom, 0px));
            gap: 6px;
            max-height: min(40vh, 330px);
            overflow-y: auto;
          }
          .choice-bubble {
            min-height: 44px;
            padding: 8px 13px 9px;
            border-radius: 14px;
          }
          .choice-text {
            font-size: 14px;
            line-height: 1.2;
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
          color: rgba(243,228,200,.92) !important;
        }
        .choice-chip.cat-friendly { background: rgba(212,168,122,.3); }
        .choice-chip.cat-flirty   { background: rgba(212,99,62,.34); color: #f0b48a !important; }
        .choice-chip.cat-deep     { background: rgba(193,154,79,.36); color: #e8cf90 !important; }
        .choice-chip.cat-banter   { background: rgba(138,165,128,.34); color: #b6d4a6 !important; }
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
