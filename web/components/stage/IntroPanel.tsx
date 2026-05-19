"use client";

import { useEffect, useState } from "react";
import type { AvailableAction, IslanderSummary, SessionState } from "../../lib/types";
import {
  INTRO_DYNAMICS,
  INTRO_RESPONSES,
  greetingFor,
  introActionsForTarget,
  nextIntroTarget,
  type IntroDynamic,
} from "../../lib/intros";
import { NpcPortrait } from "./NpcPortrait";

type Props = {
  state: SessionState;
  actions: AvailableAction[];
  pending: boolean;
  lastNpcDialogue?: string | null;
  lastPlayerLine?: string | null;
  onChoose: (action: AvailableAction, playerLine: string) => void;
};

export function IntroPanel({ state, actions, pending, lastNpcDialogue, lastPlayerLine, onChoose }: Props) {
  const target = nextIntroTarget(state.islanders, actions, state.player.id);
  const targetId = target?.id ?? null;
  const [shownTargetId, setShownTargetId] = useState<string | null>(targetId);
  useEffect(() => {
    if (targetId && targetId !== shownTargetId) setShownTargetId(targetId);
  }, [targetId, shownTargetId]);

  if (!target) {
    return (
      <div className="intro-empty">
        <p className="intro-empty-line">All introductions made. Sunset Bay is yours.</p>
        <style jsx>{`
          .intro-empty {
            display: grid;
            place-items: center;
            padding: 4vh 2vw;
            color: var(--gold-soft);
            font-family: var(--font-display);
            font-style: italic;
            font-size: 22px;
          }
        `}</style>
      </div>
    );
  }

  const choices = introActionsForTarget(actions, target.id);
  const showResponse = pending || (lastNpcDialogue && lastPlayerLine);
  const npcLine = pending
    ? "…"
    : lastNpcDialogue ?? greetingFor(target);
  const playerLine = pending ? lastPlayerLine ?? null : lastPlayerLine ?? null;

  return (
    <div
      className="intro-stage"
      data-screen="intros"
      data-state={pending ? "dialogue-streaming" : "dialogue-complete"}
    >
      <div className="intro-grid">
        <div className="intro-portrait">
          <NpcPortrait npc={target} />
        </div>

        <div className="intro-conversation">
          <header className="intro-header">
            <span className="intro-eyebrow">Day-1 Introductions</span>
            <h2 className="intro-title">Meet {target.name}</h2>
            <p className="intro-sub">{target.archetype} · at {target.location_label ?? target.location_id}</p>
          </header>

          {playerLine ? (
            <div className="bubble bubble-player">
              <span className="bubble-tag">You</span>
              <p>{playerLine}</p>
            </div>
          ) : null}

          <div className="bubble bubble-npc">
            <span className="bubble-tag">{target.name}</span>
            <p>{npcLine}</p>
          </div>

          {!showResponse ? (
            <p className="intro-prompt">How do you respond?</p>
          ) : null}
        </div>
      </div>

      <div data-testid="choice-menu" className="intro-choices">
        {INTRO_DYNAMICS.map((dynamic) => {
          const action = choices[dynamic];
          const meta = INTRO_RESPONSES[dynamic];
          return (
            <button
              key={dynamic}
              data-role="choice"
              data-testid="choice"
              data-intent={dynamic}
              disabled={pending || !action}
              onClick={() => action && onChoose(action, meta.line)}
              className={`intro-choice intro-${dynamic}`}
            >
              <span className="choice-dynamic">{meta.label}</span>
              <span className="choice-line">&ldquo;{meta.line}&rdquo;</span>
              <span className="choice-tone">{meta.tone}</span>
            </button>
          );
        })}
      </div>

      <style jsx>{`
        .intro-stage {
          flex: 1 1 auto;
          min-height: 0;
          display: grid;
          grid-template-rows: 1fr auto;
          gap: 16px;
          padding: 14px 18px 14px;
          background:
            radial-gradient(80% 60% at 50% 0, rgba(212,99,62,.06), transparent 70%),
            linear-gradient(180deg, rgba(8,6,4,.4), rgba(8,6,4,.85));
        }
        .intro-grid {
          display: grid;
          grid-template-columns: 240px 1fr;
          gap: 24px;
          align-items: center;
          min-height: 0;
        }
        @media (max-width: 900px) {
          .intro-grid { grid-template-columns: 1fr; gap: 12px; }
          .intro-portrait { justify-self: center; }
        }
        .intro-portrait { display: grid; place-items: center; }
        .intro-conversation {
          min-width: 0;
          display: grid;
          gap: 10px;
        }
        .intro-header { margin-bottom: 2px; }
        .intro-eyebrow {
          display: inline-block;
          padding: 2px 9px;
          font-size: 10px;
          letter-spacing: .14em;
          text-transform: uppercase;
          font-weight: 700;
          color: var(--gold-soft);
          background: rgba(217,167,58,.12);
          border: 1px solid rgba(217,167,58,.35);
          border-radius: var(--r-pill);
        }
        .intro-title {
          margin: 8px 0 2px;
          font-family: var(--font-display);
          font-size: clamp(24px, 3.2vw, 32px);
          font-weight: 600;
          color: var(--card);
          letter-spacing: -.01em;
        }
        .intro-sub {
          margin: 0;
          font-size: 12px;
          color: var(--muted-on-dark);
          letter-spacing: .04em;
        }

        .bubble {
          border-radius: var(--r-xl);
          padding: 12px 16px;
          box-shadow: var(--shadow-md);
        }
        .bubble-tag {
          display: inline-block;
          padding: 2px 8px;
          border-radius: var(--r-pill);
          font-size: 10px;
          font-weight: 700;
          letter-spacing: .14em;
          text-transform: uppercase;
          margin-bottom: 4px;
        }
        .bubble p { margin: 0; font-size: 15px; line-height: 1.55; }
        .bubble-npc {
          max-width: 100%;
          background: linear-gradient(180deg, var(--card-alt), var(--card));
          color: var(--ink);
          border: 1px solid var(--line);
          border-bottom-left-radius: 8px;
        }
        .bubble-npc .bubble-tag {
          background: rgba(212,99,62,.12);
          color: var(--accent-deep);
        }
        .bubble-player {
          justify-self: end;
          max-width: 80%;
          background: linear-gradient(180deg, color-mix(in oklab, var(--accent) 88%, white), var(--accent-deep));
          color: var(--card);
          border: 1px solid rgba(217,167,58,.45);
          border-bottom-right-radius: 8px;
        }
        .bubble-player .bubble-tag {
          background: rgba(255,255,255,.18);
          color: rgba(255,255,255,.95);
        }
        .intro-prompt {
          margin: 4px 0 0;
          font-size: 12px;
          font-style: italic;
          color: var(--muted-on-dark);
          letter-spacing: .04em;
        }

        .intro-choices {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 10px;
        }
        @media (max-width: 900px) {
          .intro-choices { grid-template-columns: repeat(2, 1fr); }
        }
        .intro-choice {
          display: grid;
          gap: 6px;
          padding: 12px 14px 14px;
          border-radius: var(--r-lg);
          background: linear-gradient(180deg, rgba(248,246,239,.04), rgba(248,246,239,.01)), rgba(20,16,12,.8);
          border: 1px solid rgba(248,236,210,.14);
          color: var(--ink-on-dark);
          cursor: pointer;
          text-align: left;
          transition: transform .18s cubic-bezier(.22,.61,.36,1), border-color .18s, box-shadow .18s, background .18s;
          min-height: 92px;
        }
        .intro-choice:hover:not(:disabled) {
          transform: translateY(-3px);
          background: linear-gradient(180deg, rgba(248,246,239,.07), rgba(248,246,239,.02)), rgba(28,22,16,.92);
          border-color: rgba(217,167,58,.55);
          box-shadow: var(--shadow-lg), 0 0 22px rgba(217,167,58,.15);
        }
        .intro-choice:disabled { opacity: .45; cursor: not-allowed; }
        .choice-dynamic {
          font-size: 10px;
          font-weight: 700;
          letter-spacing: .14em;
          text-transform: uppercase;
          color: var(--gold-soft);
        }
        .choice-line {
          font-family: var(--font-display);
          font-size: 14.5px;
          line-height: 1.4;
          color: var(--card);
        }
        .choice-tone {
          font-size: 11px;
          color: var(--muted-on-dark);
          opacity: .8;
          letter-spacing: .03em;
          font-style: italic;
        }
      `}</style>
    </div>
  );
}
