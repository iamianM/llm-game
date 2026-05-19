"use client";

import type { CoupleSummary } from "../../lib/types";
import { Narration } from "./Narration";
import { PairingList } from "./PairingList";

type Props = {
  title: string;
  narration: string;
  couples: CoupleSummary[];
  onContinue: () => void;
};

export function CeremonyOverlay({ title, narration, couples, onContinue }: Props) {
  const background = featureImage(title);
  return (
    <div data-screen="ceremony" className="ceremony-stage film-grain">
      <div className="ceremony-bg" aria-hidden style={{ ["--ceremony-image" as never]: `url(${background})` }} />
      <div className="ceremony-rays" aria-hidden />
      <section className="ceremony-card">
        <p className="ceremony-eyebrow flourish">Paradise Calls</p>
        <h1 className="ceremony-title gold-shimmer">{title}</h1>
        <Narration>{narration}</Narration>
        <div className="couples-wrap">
          <PairingList couples={couples} />
        </div>
        <button onClick={onContinue} className="continue-cta">
          <span>Continue</span>
          <span className="arrow">→</span>
        </button>
      </section>
      <style jsx>{`
        .ceremony-stage {
          position: fixed; inset: 0;
          z-index: 30;
          display: grid;
          place-items: center;
          padding: 6vh 4vw;
          isolation: isolate;
          animation: drift-up .55s cubic-bezier(.22,.61,.36,1) both;
        }
        .ceremony-bg {
          position: absolute; inset: 0;
          background:
            radial-gradient(60% 40% at 50% 30%, rgba(217,167,58,.22), transparent 60%),
            linear-gradient(180deg, rgba(20,16,12,.72), rgba(6,4,3,.9)),
            var(--ceremony-image);
          background-size: cover;
          background-position: center;
          backdrop-filter: blur(14px);
        }
        .ceremony-rays {
          position: absolute; inset: 0; pointer-events: none;
          background:
            conic-gradient(from 200deg at 50% 0%, transparent 0deg, rgba(217,167,58,.12) 60deg, transparent 120deg, rgba(217,167,58,.06) 180deg, transparent 240deg);
          mix-blend-mode: screen;
          opacity: .55;
          animation: ambient-pulse 7s ease-in-out infinite;
        }
        .ceremony-card {
          position: relative;
          z-index: 2;
          max-width: 740px;
          text-align: center;
          color: var(--ink-on-dark);
        }
        .ceremony-eyebrow {
          font-family: var(--font-hand);
          font-size: 22px;
          color: var(--gold-soft);
          letter-spacing: .04em;
          margin-bottom: 18px;
        }
        .ceremony-title {
          margin: 0;
          font-family: var(--font-display);
          font-size: clamp(48px, 6.5vw, 78px);
          font-weight: 600;
          line-height: 1.05;
          font-style: italic;
          letter-spacing: -.01em;
        }
        .couples-wrap {
          margin-top: 28px;
        }
        .continue-cta {
          display: inline-flex;
          align-items: center;
          gap: 12px;
          margin-top: 36px;
          padding: 14px 28px;
          border-radius: var(--r-pill);
          background: linear-gradient(180deg, var(--accent), var(--accent-deep));
          color: var(--card);
          font-family: var(--font-display);
          font-size: 18px;
          font-style: italic;
          letter-spacing: .02em;
          border: 1px solid rgba(217,167,58,.5);
          cursor: pointer;
          box-shadow: var(--shadow-lg), var(--inset-gold);
          transition: transform .18s, box-shadow .18s;
        }
        .continue-cta:hover {
          transform: translateY(-2px);
          box-shadow: var(--shadow-lg), var(--shadow-accent), var(--inset-gold);
        }
        .continue-cta .arrow { transition: transform .2s; }
        .continue-cta:hover .arrow { transform: translateX(4px); }
      `}</style>
    </div>
  );
}

function featureImage(title: string) {
  if (/flush/i.test(title)) return "/images/features/flush-of-hearts.webp";
  if (/paradise calls/i.test(title)) return "/images/features/paradise-calls.webp";
  if (/first spark|pairing|heart swap|heart out/i.test(title)) return "/images/features/first-spark.webp";
  return "/images/features/first-spark.webp";
}
