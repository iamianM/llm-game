"use client";

import { useEffect, useMemo, useState } from "react";
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
  /** Called when the player advances past the final intro (no next target). */
  onIntrosDone?: () => void;
};

type InFlight = { targetId: string; playerLine: string };
type Completed = { targetId: string; playerLine: string; npcLine: string };

export function IntroPanel({
  state,
  actions,
  pending,
  lastNpcDialogue,
  lastPlayerLine,
  onChoose,
  onIntrosDone,
}: Props) {
  const islandersById = useMemo(
    () => Object.fromEntries(state.islanders.map((islander) => [islander.id, islander])),
    [state.islanders],
  );
  const nextTarget = nextIntroTarget(state.islanders, actions, state.player.id);

  // Snapshot of who the player is currently talking to and what they said. Set
  // on click, cleared once the response is captured into `completed`.
  const [inFlight, setInFlight] = useState<InFlight | null>(null);
  // Holds the just-finished exchange so the player can read the NPC's reply
  // against the correct speaker before the next NPC takes over.
  const [completed, setCompleted] = useState<Completed | null>(null);

  // When a turn finishes, promote `inFlight` into `completed` using the NPC
  // reply the server returned. This keeps the previous NPC on screen until the
  // player clicks Continue, even though `nextTarget` has already advanced.
  useEffect(() => {
    if (pending) return;
    if (!inFlight) return;
    if (!lastNpcDialogue) return;
    setCompleted({
      targetId: inFlight.targetId,
      playerLine: inFlight.playerLine,
      npcLine: lastNpcDialogue,
    });
    setInFlight(null);
  }, [pending, inFlight, lastNpcDialogue]);

  // Resolve who to render. While in flight or showing the completed exchange,
  // we render that NPC. Otherwise we render the next fresh intro target.
  const displayTargetId = inFlight?.targetId ?? completed?.targetId ?? nextTarget?.id ?? null;
  const displayTarget: IslanderSummary | null = displayTargetId
    ? islandersById[displayTargetId] ?? null
    : null;

  if (!displayTarget) {
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

  const isCompleted = completed?.targetId === displayTarget.id;
  const isStreaming = pending && inFlight?.targetId === displayTarget.id;
  const choices = !isCompleted && !isStreaming ? introActionsForTarget(actions, displayTarget.id) : {};

  // What goes in each bubble at each step:
  // - fresh: NPC greeting, no player bubble
  // - in flight: player's chosen line, NPC bubble shows ellipsis while we stream
  // - completed: player's chosen line, NPC's actual reply
  const playerBubble = isCompleted
    ? completed.playerLine
    : isStreaming
      ? inFlight.playerLine
      : null;
  const npcBubble = isCompleted
    ? completed.npcLine
    : isStreaming
      ? "…"
      : greetingFor(displayTarget);

  const handleChoose = (action: AvailableAction, line: string) => {
    setInFlight({ targetId: displayTarget.id, playerLine: line });
    setCompleted(null);
    onChoose(action, line);
  };

  const handleContinue = () => {
    setCompleted(null);
    if (!nextTarget) onIntrosDone?.();
  };

  return (
    <div
      className="intro-stage"
      data-screen="intros"
      data-state={isCompleted ? "exchange-complete" : isStreaming ? "dialogue-streaming" : "ready"}
    >
      <div className="intro-grid">
        <div className="intro-portrait">
          <NpcPortrait npc={displayTarget} />
        </div>

        <div className="intro-conversation">
          <header className="intro-header">
            <span className="intro-eyebrow">Day-1 Introductions</span>
            <h2 className="intro-title">Meet {displayTarget.name}</h2>
            <p className="intro-sub">
              {displayTarget.archetype} · at {displayTarget.location_label ?? displayTarget.location_id}
            </p>
          </header>

          {playerBubble ? (
            <div className="bubble bubble-player">
              <span className="bubble-tag">You</span>
              <p>{playerBubble}</p>
            </div>
          ) : null}

          <div className="bubble bubble-npc">
            <span className="bubble-tag">{displayTarget.name}</span>
            <p>{npcBubble}</p>
          </div>

          {!isCompleted && !isStreaming ? (
            <p className="intro-prompt">How do you respond?</p>
          ) : null}
        </div>
      </div>

      {isCompleted ? (
        <div className="intro-continue">
          <button data-role="continue" data-testid="intro-continue" onClick={handleContinue} className="continue-btn">
            <span className="continue-label">{nextTarget ? `Continue → meet ${nextTarget.name}` : "Continue"}</span>
            <span className="continue-arrow">→</span>
          </button>
        </div>
      ) : (
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
                disabled={isStreaming || !action}
                onClick={() => action && handleChoose(action, meta.line)}
                className={`intro-choice intro-${dynamic}`}
              >
                <span className="choice-dynamic">{meta.label}</span>
                <span className="choice-line">&ldquo;{meta.line}&rdquo;</span>
                <span className="choice-tone">{meta.tone}</span>
              </button>
            );
          })}
        </div>
      )}

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

        .intro-continue {
          display: grid;
          justify-content: end;
        }
        .continue-btn {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          padding: 12px 22px;
          font-family: var(--font-display);
          font-size: 16px;
          font-style: italic;
          color: var(--card);
          background: linear-gradient(180deg, var(--accent), var(--accent-deep));
          border: 1px solid rgba(217,167,58,.55);
          border-radius: var(--r-pill);
          cursor: pointer;
          box-shadow: var(--shadow-md), var(--inset-gold);
          transition: transform .18s, box-shadow .18s;
        }
        .continue-btn:hover {
          transform: translateY(-2px);
          box-shadow: var(--shadow-lg), var(--shadow-accent), var(--inset-gold);
        }
        .continue-arrow { font-style: normal; font-size: 18px; }
      `}</style>
    </div>
  );
}
