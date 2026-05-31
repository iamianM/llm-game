"use client";

import { ChevronRight } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { type CSSProperties, useEffect, useRef } from "react";
import type { Position } from "../../lib/scene/types";
import { useTypewriter } from "../../lib/scene/typewriter";

type Props = {
  anchorId: string;
  role: "player" | "npc";
  speaker: string;
  text: string;
  position: Position;
  canAdvance: boolean;
};

export function SpeechBubble({ anchorId, role, speaker, text, position, canAdvance }: Props) {
  const reduce = useReducedMotion();
  const { rendered, complete, revealAll } = useTypewriter(text);
  // First scene-tap completes the streaming; the second tap (caught upstream
  // by SceneLayer) advances to the next beat. We listen to the same
  // background-tap event by exposing revealAll via a ref that
  // SceneDialogueStage can call.
  const revealRef = useRef(revealAll);
  useEffect(() => { revealRef.current = revealAll; }, [revealAll]);
  const style = {
    "--bubble-left": `${position.x}%`,
    "--bubble-top": `${Math.max(10, position.y - (role === "player" ? 31 : 33))}%`,
  } as CSSProperties;
  return (
    <div
      data-testid={role === "player" ? "player-bubble" : "speech-bubble"}
      data-anchor-id={anchorId}
      data-stream-complete={complete ? "true" : "false"}
      className="speech-bubble-shell"
      style={style}
    >
      <motion.div
        className={`speech-bubble bubble-${role}`}
        initial={reduce ? false : { opacity: 0, scale: 0.92, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={reduce ? { duration: 0.06 } : { duration: 0.18, ease: "easeOut" }}
      >
        <span className="speaker-chip">{speaker}</span>
        <p>
          {rendered}
          {!complete ? <span className="cursor" aria-hidden>▍</span> : null}
        </p>
        {canAdvance && complete ? <ChevronRight className="advance" size={18} /> : null}
        <span className="tail" aria-hidden />
      </motion.div>
      <style jsx global>{`
        .speech-bubble-shell {
          position: absolute;
          --bubble-width: min(460px, calc(100vw - 32px));
          left: clamp(
            calc(var(--bubble-width) / 2 + 12px),
            var(--bubble-left),
            calc(100% - var(--bubble-width) / 2 - 12px)
          );
          top: var(--bubble-top);
          z-index: 8;
          width: var(--bubble-width);
          transform: translateX(-50%);
          pointer-events: none;
        }
        .speech-bubble {
          position: relative;
          width: 100%;
          min-height: 76px;
          /* Extra top padding clears the name chip that floats over the edge. */
          padding: 22px 18px 16px;
          margin-top: 12px;
          border-radius: 22px;
          background: #fffdf8;
          border: 1px solid rgba(217,167,58,.3);
          box-shadow: var(--shadow-lg);
          color: var(--ink);
          pointer-events: none;
        }
        .bubble-player {
          background: linear-gradient(180deg, #fff8ec, #fdeecf);
          border-color: rgba(217,167,58,.5);
        }
        .speaker-chip {
          position: absolute;
          top: -13px;
          left: 16px;
          padding: 4px 13px 5px;
          border-radius: var(--r-pill);
          background: linear-gradient(180deg, var(--accent), var(--accent-deep));
          color: #fff;
          font-family: var(--font-display);
          font-size: 14px;
          font-weight: 700;
          letter-spacing: .01em;
          line-height: 1;
          box-shadow: 0 4px 12px rgba(0,0,0,.28);
          white-space: nowrap;
        }
        .bubble-player .speaker-chip {
          background: linear-gradient(180deg, #2a211a, #14100c);
          color: var(--accent);
        }
        p {
          margin: 0;
          font-size: 17px;
          line-height: 1.42;
        }
        .cursor {
          display: inline-block;
          margin-left: 1px;
          font-weight: 400;
          opacity: .55;
          animation: cursor-blink 1.1s steps(2, end) infinite;
        }
        @keyframes cursor-blink {
          50% { opacity: 0; }
        }
        .advance {
          position: absolute;
          right: 12px;
          bottom: 10px;
          color: currentColor;
          opacity: .55;
          animation: nudge 1.1s ease-in-out infinite;
        }
        .tail {
          position: absolute;
          left: 30px;
          bottom: -9px;
          width: 20px;
          height: 20px;
          transform: rotate(45deg);
          background: #fffdf8;
          border-right: 1px solid rgba(217,167,58,.3);
          border-bottom: 1px solid rgba(217,167,58,.3);
        }
        .bubble-player .tail {
          background: #fdeecf;
          border-color: rgba(217,167,58,.5);
        }
        @keyframes nudge {
          0%, 100% { transform: translateX(0); }
          50% { transform: translateX(3px); }
        }
        @media (max-width: 520px) {
          .speech-bubble-shell {
            --bubble-width: min(338px, calc(100vw - 24px));
          }
          .speech-bubble {
            min-height: 70px;
            padding: 20px 15px 13px;
            border-radius: 18px;
          }
          .speaker-chip { font-size: 12.5px; left: 13px; }
          .tail { left: 24px; }
          p { font-size: 15.5px; line-height: 1.38; }
        }
      `}</style>
    </div>
  );
}
