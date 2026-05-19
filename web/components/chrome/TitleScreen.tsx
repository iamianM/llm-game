"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export function TitleScreen() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  return (
    <main className="title-stage film-grain vignette">
      {/* Sunset layers */}
      <div className="title-sky" aria-hidden />
      <div className="title-horizon" aria-hidden />
      <div className="title-water" aria-hidden />
      <div className="title-palms" aria-hidden>
        <span className="palm palm-l" />
        <span className="palm palm-r" />
      </div>

      <section className={`title-content ${mounted ? "drift-in" : ""}`}>
        <div className="title-eyebrow flourish">A Paradise Hearts Production</div>
        <h1 className="title-wordmark">
          <span className="line-1">Paradise</span>
          <span className="line-2 gold-shimmer">Hearts</span>
        </h1>
        <p className="title-tagline">Make a Connection. Survive the Drama.</p>

        <div className="title-actions">
          <Link href="/new-run" className="cta cta-primary" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
            <span className="cta-label">New Run</span>
            <span className="cta-sub">Step into Sunset Bay</span>
          </Link>
          <button className="cta cta-secondary" disabled>
            <span className="cta-label">Continue Run</span>
            <span className="cta-sub">No run in progress</span>
          </button>
          <button className="cta cta-secondary" disabled>
            <span className="cta-label">The Reunion</span>
            <span className="cta-sub">Unlocks in Phase 4</span>
          </button>
        </div>

        <div className="title-footer flourish">MVP build</div>
      </section>

      <style jsx>{`
        .title-stage {
          position: relative;
          height: 100vh;
          height: 100svh;
          overflow: hidden;
          background: var(--bg-deep);
          color: var(--ink-on-dark);
          display: grid;
          place-items: center;
          padding: 3vh 6vw;
          isolation: isolate;
        }
        .title-sky {
          position: absolute; inset: 0;
          background:
            linear-gradient(180deg, rgba(7,5,4,.08), rgba(7,5,4,.82)),
            url("/images/features/title-sunset-bay.webp"),
            var(--grad-title);
          background-size: cover;
          background-position: center;
          z-index: 0;
        }
        .title-horizon {
          position: absolute;
          left: 0; right: 0;
          top: 56%;
          height: 2px;
          background: linear-gradient(90deg, transparent, rgba(248,236,210,.55), transparent);
          z-index: 1;
          filter: blur(.4px);
        }
        .title-water {
          position: absolute;
          left: 0; right: 0; bottom: 0;
          height: 44%;
          background: linear-gradient(180deg, rgba(20,38,56,.55), rgba(8,16,26,.95));
          z-index: 1;
          opacity: .8;
        }
        .title-water::after {
          content: "";
          position: absolute;
          inset: 0;
          background:
            repeating-linear-gradient(180deg, transparent 0 6px, rgba(248,236,210,.03) 6px 7px),
            radial-gradient(120% 60% at 50% 0, rgba(212,99,62,.25), transparent 70%);
          mix-blend-mode: screen;
        }
        .title-palms {
          position: absolute; inset: 0; pointer-events: none; z-index: 2;
        }
        .palm {
          position: absolute;
          bottom: 32%;
          width: 220px; height: 70vh;
          background: radial-gradient(120% 60% at 50% 100%, rgba(0,0,0,.85), rgba(0,0,0,.55) 30%, transparent 60%);
          filter: blur(2px);
        }
        .palm-l { left: -100px; }
        .palm-r { right: -100px; transform: scaleX(-1); }

        .title-content {
          position: relative;
          z-index: 5;
          text-align: center;
          max-width: 720px;
        }
        .title-eyebrow {
          font-family: var(--font-hand);
          font-size: 16px;
          color: var(--gold-soft);
          letter-spacing: .04em;
          opacity: .9;
        }
        .title-wordmark {
          margin: 10px 0 0;
          line-height: 0.92;
          font-family: var(--font-display);
          font-weight: 700;
          letter-spacing: -.02em;
        }
        .line-1 {
          display: block;
          font-size: clamp(40px, 9vh, 112px);
          color: var(--card);
          text-shadow: 0 4px 22px rgba(0,0,0,.55);
        }
        .line-2 {
          display: block;
          font-size: clamp(56px, 13vh, 160px);
          font-style: italic;
          letter-spacing: -.03em;
        }
        .title-tagline {
          margin-top: 12px;
          font-family: var(--font-display);
          font-style: italic;
          font-size: clamp(14px, 1.6vw, 19px);
          color: var(--gold-soft);
          letter-spacing: .04em;
          opacity: .95;
        }

        .title-actions {
          margin: 28px auto 0;
          display: grid;
          grid-template-columns: 1fr;
          gap: 10px;
          max-width: 360px;
        }
        .cta {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 3px;
          padding: 12px 22px;
          border-radius: var(--r-lg);
          cursor: pointer;
          transition: transform .18s cubic-bezier(.22,.61,.36,1), box-shadow .18s, border-color .18s;
          border: var(--frame-gold);
          text-decoration: none;
          color: var(--ink-on-dark);
        }
        .cta-label {
          font-family: var(--font-display);
          font-size: 20px;
          letter-spacing: .02em;
        }
        .cta-sub {
          font-size: 11px;
          letter-spacing: .14em;
          text-transform: uppercase;
          color: var(--gold-soft);
          opacity: .8;
        }
        .cta-primary {
          background: linear-gradient(180deg, var(--accent), var(--accent-deep));
          color: var(--card);
          border-color: rgba(217,167,58,.6);
          box-shadow: var(--shadow-md), var(--inset-gold);
        }
        .cta-primary:hover {
          transform: translateY(-2px);
          box-shadow: var(--shadow-lg), var(--shadow-accent), var(--inset-gold);
        }
        .cta-secondary {
          background: rgba(20,16,12,.6);
          backdrop-filter: blur(6px);
          color: var(--muted-on-dark);
        }
        .cta-secondary[disabled] {
          cursor: not-allowed;
          opacity: .55;
        }
        .cta-secondary:not([disabled]):hover {
          border-color: rgba(217,167,58,.55);
          color: var(--ink-on-dark);
        }

        .title-footer {
          margin-top: 28px;
          font-family: var(--font-hand);
          font-size: 13px;
          color: rgba(248,236,210,.5);
          letter-spacing: .04em;
        }
      `}</style>
    </main>
  );
}
