"use client";

import { ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { useUiStore } from "../../lib/store";
import { DeltaChip } from "./DeltaChip";

type Props = {
  speaker: string;
  text: string;
  playerLine?: string;
  complete?: boolean;
  audienceDelta?: number | null;
  audienceReason?: string | null;
  onAdvance?: () => void;
};

export function DialogueBox({ speaker, text, playerLine, complete = true, audienceDelta, audienceReason, onAdvance }: Props) {
  const speed = useUiStore((s) => s.typewriterSpeed);
  const reduce = useUiStore((s) => s.reduceMotion);
  const [visible, setVisible] = useState(text);
  useEffect(() => {
    if (!complete) { setVisible(text); return; }
    if (speed === "instant" || reduce) { setVisible(text); return; }
    setVisible("");
    const interval = speed === "slow" ? 45 : speed === "fast" ? 12 : 24;
    let index = 0;
    const timer = window.setInterval(() => {
      index += 1;
      setVisible(text.slice(0, index));
      if (index >= text.length) window.clearInterval(timer);
    }, interval);
    return () => window.clearInterval(timer);
  }, [text, speed, reduce, complete]);

  function handleClick() {
    if (visible !== text) { setVisible(text); return; }
    if (complete) onAdvance?.();
  }

  return (
    <section onClick={handleClick} className="dialogue-stage">
      <div className="dialogue-grid">
        {playerLine ? (
          <div className="bubble bubble-player">
            <span className="bubble-tag">You</span>
            <p>{playerLine}</p>
          </div>
        ) : null}
        <div className="bubble bubble-npc">
          <header className="npc-header">
            <span className="npc-name">{speaker}</span>
            <DeltaChip delta={audienceDelta} reason={audienceReason} />
          </header>
          <p aria-live="polite" className="npc-line">{visible || "…"}</p>
          <div
            data-state={visible === text && complete ? "dialogue-complete" : "dialogue-streaming"}
            className="npc-advance"
          >
            {visible === text ? <ChevronRight size={20} /> : <span className="dots"><span/><span/><span/></span>}
          </div>
        </div>
      </div>

      <style jsx>{`
        .dialogue-stage {
          position: relative;
          background:
            linear-gradient(180deg, rgba(0,0,0,.15), rgba(0,0,0,.55)),
            linear-gradient(180deg, rgba(20,16,12,.85), rgba(8,6,4,.95));
          border-top: 1px solid rgba(217,167,58,.18);
          padding: 18px 18px 14px;
          cursor: pointer;
          flex: 0 0 auto;
        }
        .dialogue-grid {
          max-width: 1080px;
          margin: 0 auto;
          display: grid;
          gap: 10px;
        }
        .bubble {
          border-radius: var(--r-xl);
          padding: 14px 18px;
          box-shadow: var(--shadow-lg);
          backdrop-filter: blur(8px);
        }
        .bubble-tag {
          display: inline-block;
          padding: 2px 9px;
          border-radius: var(--r-pill);
          font-size: 11px;
          font-weight: 700;
          letter-spacing: .14em;
          text-transform: uppercase;
          margin-bottom: 6px;
        }
        .bubble-player {
          justify-self: end;
          max-width: 70%;
          background: linear-gradient(180deg, color-mix(in oklab, var(--accent) 88%, white), var(--accent-deep));
          color: var(--card);
          border-bottom-right-radius: 8px;
          border: 1px solid rgba(217,167,58,.45);
        }
        .bubble-player .bubble-tag {
          background: rgba(255,255,255,.18);
          color: rgba(255,255,255,.95);
        }
        .bubble-player p {
          margin: 0;
          font-size: 14px;
          line-height: 1.55;
        }

        .bubble-npc {
          justify-self: start;
          max-width: 80%;
          background:
            linear-gradient(180deg, var(--card-alt), var(--card)),
            radial-gradient(40% 60% at 0 0, rgba(217,167,58,.08), transparent 60%);
          color: var(--ink);
          border-bottom-left-radius: 8px;
          border: 1px solid var(--line);
          position: relative;
        }
        .bubble-npc::before {
          content: "";
          position: absolute;
          inset: 0;
          border-radius: inherit;
          padding: 1px;
          background: linear-gradient(180deg, rgba(217,167,58,.4), transparent 50%);
          -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
          mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
          -webkit-mask-composite: xor;
          mask-composite: exclude;
          pointer-events: none;
        }
        .npc-header {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 4px;
        }
        .npc-name {
          font-family: var(--font-display);
          font-size: 22px;
          font-weight: 600;
          color: var(--accent-deep);
          letter-spacing: .01em;
        }
        .npc-line {
          margin: 4px 0 6px;
          font-size: 17px;
          line-height: 1.6;
          color: var(--ink);
          min-height: 1.6em;
        }
        .npc-advance {
          display: flex;
          justify-content: flex-end;
          color: var(--accent);
        }
        .dots { display: inline-flex; gap: 4px; align-items: center; }
        .dots span {
          width: 5px; height: 5px;
          border-radius: 50%;
          background: var(--accent);
          opacity: .4;
          animation: dot-pulse 1.3s ease-in-out infinite;
        }
        .dots span:nth-child(2) { animation-delay: .18s; }
        .dots span:nth-child(3) { animation-delay: .36s; }
        @keyframes dot-pulse {
          0%, 100% { opacity: .25; transform: translateY(0); }
          50% { opacity: 1; transform: translateY(-2px); }
        }
      `}</style>
    </section>
  );
}
