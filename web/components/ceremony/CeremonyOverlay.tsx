"use client";

import type { CoupleSummary } from "../../lib/types";
import { Narration } from "./Narration";
import { PairingList } from "./PairingList";

type Props = {
  title: string;
  eyebrow: string;
  narration: string;
  couples: CoupleSummary[];
  showCouples: boolean;
  onContinue: () => void;
};

export function CeremonyOverlay({ title, eyebrow, narration, couples, showCouples, onContinue }: Props) {
  const background = featureImage(title);
  return (
    <div data-screen="ceremony" className="ceremony-stage film-grain">
      <div className="ceremony-bg" aria-hidden style={{ ["--ceremony-image" as never]: `url(${background})` }} />
      <div className="ceremony-rays" aria-hidden />
      <section className="ceremony-card" role="dialog" aria-modal="true" aria-labelledby="ceremony-title">
        <div className="ceremony-copy">
          <p className="ceremony-eyebrow flourish">{eyebrow}</p>
          <h1 id="ceremony-title" className="ceremony-title gold-shimmer">{title}</h1>
        </div>
        <div className="ceremony-scroll">
          <Narration>{narration}</Narration>
          {showCouples ? (
            <div className="couples-wrap">
              <PairingList couples={couples} />
            </div>
          ) : null}
        </div>
        <div className="ceremony-actions">
          <button onClick={onContinue} className="continue-cta">
            <span>Continue</span>
            <span className="arrow">→</span>
          </button>
        </div>
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
          display: grid;
          grid-template-rows: auto minmax(0, 1fr) auto;
          max-width: 740px;
          width: min(740px, 100%);
          max-height: min(760px, calc(100svh - 36px));
          padding: 0 12px;
          text-align: center;
          color: var(--ink-on-dark);
          overflow: hidden;
        }
        .ceremony-copy { flex: 0 0 auto; }
        .ceremony-eyebrow {
          font-family: var(--font-hand);
          font-size: 22px;
          color: var(--gold-soft);
          letter-spacing: .04em;
          margin: 0 0 14px;
        }
        .ceremony-title {
          margin: 0;
          font-family: var(--font-display);
          font-size: clamp(38px, 6vw, 74px);
          font-weight: 600;
          line-height: 1.05;
          font-style: italic;
          letter-spacing: 0;
        }
        .ceremony-scroll {
          min-height: 0;
          overflow-y: auto;
          padding: 18px 4px 4px;
          scrollbar-width: thin;
        }
        .couples-wrap {
          margin-top: 22px;
        }
        .ceremony-actions {
          position: sticky;
          bottom: 0;
          padding: 18px 0 2px;
          background: linear-gradient(180deg, transparent, rgba(6,4,3,.78) 28%, rgba(6,4,3,.94));
        }
        .continue-cta {
          display: inline-flex;
          align-items: center;
          gap: 12px;
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
        @media (max-height: 760px) {
          .ceremony-stage { padding: 18px 3vw; }
          .ceremony-eyebrow { font-size: 18px; margin-bottom: 8px; }
          .ceremony-title { font-size: clamp(34px, 5.5vw, 58px); }
          .ceremony-scroll { padding-top: 12px; }
          .ceremony-actions { padding-top: 12px; }
        }
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
