"use client";

import { ChevronRight } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { useTypewriter } from "../../lib/scene/typewriter";

export function NarratorBubble({ text, canAdvance, withBanner = false }: { text: string; canAdvance: boolean; withBanner?: boolean }) {
  const reduce = useReducedMotion();
  const { rendered, complete } = useTypewriter(text);
  return (
    <div data-testid="narrator-bubble" data-stream-complete={complete ? "true" : "false"} className={`narrator-shell${withBanner ? " has-banner" : ""}`}>
      <motion.div
        className="narrator-bubble"
        initial={reduce ? false : { opacity: 0, y: -10, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={reduce ? { duration: 0.06 } : { duration: 0.2, ease: "easeOut" }}
      >
        <span>The Producer</span>
        <p>
          {rendered}
          {!complete ? <span className="narrator-cursor" aria-hidden>▍</span> : null}
        </p>
        {canAdvance && complete ? <ChevronRight className="advance" size={18} /> : null}
      </motion.div>
      <style jsx global>{`
        .narrator-shell {
          position: absolute;
          z-index: 9;
          top: 12px;
          left: 50%;
          transform: translateX(-50%);
          width: min(680px, calc(100vw - 28px));
          pointer-events: none;
        }
        .narrator-bubble {
          position: relative;
          padding: 12px 18px 14px;
          border-radius: var(--r-xl);
          background:
            linear-gradient(180deg, rgba(248,246,239,.96), rgba(242,231,205,.94)),
            radial-gradient(80% 80% at 50% 0, rgba(217,167,58,.18), transparent 65%);
          border: 1px solid rgba(217,167,58,.5);
          color: var(--ink);
          box-shadow: var(--shadow-lg), var(--inset-gold);
          text-align: center;
        }
        .narrator-bubble > span {
          display: block;
          font-family: var(--font-hand);
          color: var(--accent-deep);
          font-size: 13px;
          letter-spacing: .12em;
          text-transform: uppercase;
        }
        .narrator-bubble > p {
          margin: 4px 0 0;
          font-family: var(--font-display);
          font-style: italic;
          font-size: clamp(16px, 2.2vw, 22px);
          line-height: 1.3;
        }
        .narrator-cursor {
          display: inline-block;
          margin-left: 1px;
          font-style: normal;
          font-weight: 400;
          opacity: .5;
          animation: narrator-cursor-blink 1.1s steps(2, end) infinite;
        }
        @keyframes narrator-cursor-blink {
          50% { opacity: 0; }
        }
        .narrator-bubble .advance {
          position: absolute;
          right: 12px;
          bottom: 10px;
          color: var(--accent);
          opacity: .55;
          animation: nudge 1.1s ease-in-out infinite;
        }
        @media (max-width: 520px) {
          .narrator-shell { top: 8px; }
          /* Clear the challenge round chip (top-left) so the centered
             "The Producer" label never tucks under it on narrow screens. */
          .narrator-shell.has-banner { top: 52px; }
          .narrator-bubble {
            padding: 9px 12px 11px;
            border-radius: var(--r-lg);
          }
          .narrator-bubble > p { font-size: 15px; }
          .narrator-bubble > span { font-size: 11px; }
        }
        @keyframes nudge {
          0%, 100% { transform: translateX(0); }
          50% { transform: translateX(3px); }
        }
      `}</style>
    </div>
  );
}
