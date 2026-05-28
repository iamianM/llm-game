"use client";

import { ChevronRight } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";

export function NarratorBubble({ text, canAdvance }: { text: string; canAdvance: boolean }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      data-testid="narrator-bubble"
      className="narrator-bubble"
      initial={reduce ? false : { opacity: 0, y: -10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={reduce ? { duration: 0.06 } : { duration: 0.2, ease: "easeOut" }}
    >
      <span>The Producer</span>
      <p>{text}</p>
      {canAdvance ? <ChevronRight className="advance" size={18} /> : null}
      <style jsx global>{`
        .narrator-bubble {
          position: absolute;
          z-index: 9;
          top: 12px;
          left: 50%;
          transform: translateX(-50%);
          width: min(760px, calc(100vw - 28px));
          padding: 12px 18px 14px;
          border-radius: var(--r-xl);
          background:
            linear-gradient(180deg, rgba(248,246,239,.96), rgba(242,231,205,.94)),
            radial-gradient(80% 80% at 50% 0, rgba(217,167,58,.18), transparent 65%);
          border: 1px solid rgba(217,167,58,.5);
          color: var(--ink);
          box-shadow: var(--shadow-lg), var(--inset-gold);
          pointer-events: none;
          text-align: center;
        }
        span {
          font-family: var(--font-hand);
          color: var(--accent-deep);
          font-size: 14px;
          letter-spacing: .12em;
          text-transform: uppercase;
        }
        p {
          margin: 4px 0 0;
          font-family: var(--font-display);
          font-style: italic;
          font-size: clamp(18px, 2.4vw, 25px);
          line-height: 1.28;
        }
        .advance {
          position: absolute;
          right: 12px;
          bottom: 10px;
          color: var(--accent);
          opacity: .55;
        }
        @media (max-width: 520px) {
          .narrator-bubble {
            top: 9px;
            padding: 10px 14px 12px;
            border-radius: var(--r-lg);
          }
          p { font-size: 17px; }
        }
      `}</style>
    </motion.div>
  );
}
