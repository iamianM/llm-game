"use client";

import { ChevronRight } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import type { CSSProperties } from "react";
import type { Position } from "../../lib/scene/types";

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
  const style = {
    "--bubble-left": `${position.x}%`,
    "--bubble-top": `${Math.max(10, position.y - (role === "player" ? 31 : 33))}%`,
  } as CSSProperties;
  return (
    <div
      data-testid={role === "player" ? "player-bubble" : "speech-bubble"}
      data-anchor-id={anchorId}
      className="speech-bubble-shell"
      style={style}
    >
      <motion.div
        className={`speech-bubble bubble-${role}`}
        initial={reduce ? false : { opacity: 0, scale: 0.92, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={reduce ? { duration: 0.06 } : { duration: 0.18, ease: "easeOut" }}
      >
        <span className="speaker">{speaker}</span>
        <p>{text}</p>
        {canAdvance ? <ChevronRight className="advance" size={18} /> : null}
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
          min-height: 86px;
          padding: 14px 18px 16px;
          border-radius: 24px;
          background: linear-gradient(180deg, var(--card-alt), var(--card));
          border: 1px solid rgba(217,167,58,.42);
          box-shadow: var(--shadow-lg), var(--inset-gold);
          color: var(--ink);
          pointer-events: none;
        }
        .bubble-player {
          background: linear-gradient(180deg, color-mix(in oklab, var(--accent) 82%, white), var(--accent-deep));
          color: var(--card);
          border-color: rgba(217,167,58,.65);
        }
        .speaker {
          display: block;
          font-family: var(--font-display);
          font-size: 20px;
          font-weight: 700;
          color: var(--accent-deep);
          line-height: 1;
        }
        .bubble-player .speaker {
          color: rgba(255,255,255,.9);
        }
        p {
          margin: 8px 0 0;
          font-size: 17px;
          line-height: 1.42;
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
          left: 50%;
          bottom: -10px;
          width: 22px;
          height: 22px;
          transform: translateX(-50%) rotate(45deg);
          background: inherit;
          border-right: 1px solid rgba(217,167,58,.32);
          border-bottom: 1px solid rgba(217,167,58,.32);
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
            min-height: 78px;
            padding: 12px 15px 14px;
            border-radius: 20px;
          }
          .speaker { font-size: 18px; }
          p { font-size: 15.5px; line-height: 1.38; }
        }
      `}</style>
    </div>
  );
}
