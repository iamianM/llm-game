"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getCurrentSessionId, sessionStore } from "../../lib/storage";
import { playSfx } from "../../lib/sfx";
import { useUiStore } from "../../lib/store";

export function TitleScreen() {
  const [mounted, setMounted] = useState(false);
  const [resumeSessionId, setResumeSessionId] = useState<string | null>(null);
  const soundOn = useUiStore((s) => s.musicOn);
  const volume = useUiStore((s) => s.musicVolume);
  const setMusicOn = useUiStore((s) => s.setMusicOn);
  const setMusicVolume = useUiStore((s) => s.setMusicVolume);

  useEffect(() => {
    setMounted(true);
    const sid = getCurrentSessionId();
    if (sid && sessionStore.load(sid)) {
      setResumeSessionId(sid);
    }
  }, []);

  const toggleSound = () => {
    setMusicOn(!soundOn);
  };

  const handleVolume = (e: React.ChangeEvent<HTMLInputElement>) => {
    const next = Number(e.target.value) / 100;
    setMusicVolume(next);
    if (next > 0 && !soundOn) {
      setMusicOn(true);
    }
  };

  return (
    <main className="title-stage film-grain vignette">
      <div className="sound-controls">
        <button
          type="button"
          className="sound-toggle"
          onClick={toggleSound}
          aria-label={soundOn ? "Mute music" : "Play music"}
          aria-pressed={soundOn}
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden focusable="false">
            <path
              d="M4 9v6h4l5 4V5L8 9H4z"
              fill="currentColor"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinejoin="round"
            />
            {soundOn ? (
              <>
                <path d="M16.5 8.5a5 5 0 0 1 0 7" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                <path d="M19 6a8.5 8.5 0 0 1 0 12" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              </>
            ) : (
              <path d="M16.5 9.5l5 5m0-5l-5 5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            )}
          </svg>
        </button>
        <input
          type="range"
          className="volume-slider"
          min={0}
          max={100}
          value={Math.round(volume * 100)}
          onChange={handleVolume}
          aria-label="Music volume"
        />
      </div>
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
          <Link href="/create" onClick={() => playSfx("new-run")} className="cta cta-primary" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
            <span className="cta-label">New Run</span>
            <span className="cta-sub">Choose your Islander</span>
          </Link>
          {resumeSessionId ? (
            <Link
              href={`/play/${resumeSessionId}`}
              className="cta cta-secondary cta-active"
              style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}
            >
              <span className="cta-label">Continue Run</span>
              <span className="cta-sub">Pick up where you left off</span>
            </Link>
          ) : (
            <button className="cta cta-secondary" disabled>
              <span className="cta-label">Continue Run</span>
              <span className="cta-sub">No run in progress</span>
            </button>
          )}
        </div>

        <div className="title-footer flourish">Tonight, everything counts</div>
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
          /* Cap by width as well as height so the wordmark never overflows a
             tall, narrow phone (vh alone clipped "Hearts" off the edge). */
          font-size: clamp(40px, min(9vh, 16vw), 112px);
          color: var(--card);
          text-shadow: 0 4px 22px rgba(0,0,0,.55);
        }
        .line-2 {
          display: block;
          font-size: clamp(50px, min(13vh, 21vw), 160px);
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
        /* next/link renders a custom <Link> component, and styled-jsx does NOT
           inject its scoping class into custom components — only native tags.
           So .cta rules applied directly to a <Link> never matched, leaving the
           primary CTA (and the resume "Continue Run" link) unstyled. Scope via
           the native .title-actions wrapper and target the links with :global so
           the rules reach both <Link> and <button> CTAs consistently. */
        .title-actions :global(.cta) {
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
        .title-actions :global(.cta-label) {
          font-family: var(--font-display);
          font-size: 20px;
          letter-spacing: .02em;
        }
        .title-actions :global(.cta-sub) {
          font-size: 11px;
          letter-spacing: .14em;
          text-transform: uppercase;
          color: var(--gold-soft);
          opacity: .8;
        }
        .title-actions :global(.cta-primary) {
          background: linear-gradient(180deg, var(--accent), var(--accent-deep));
          color: var(--card);
          border-color: rgba(247,210,120,.9);
          /* Persistent accent glow + ring so the primary action stays the most
             prominent element even against the warm sunset backdrop. */
          box-shadow: var(--shadow-lg), var(--shadow-accent), var(--inset-gold),
            0 0 0 1px rgba(247,210,120,.35);
        }
        .title-actions :global(.cta-primary:hover) {
          transform: translateY(-2px);
          box-shadow: var(--shadow-lg), var(--shadow-accent), var(--inset-gold);
        }
        .title-actions :global(.cta-secondary) {
          background: rgba(20,16,12,.6);
          backdrop-filter: blur(6px);
          color: var(--muted-on-dark);
        }
        .title-actions :global(.cta-secondary[disabled]) {
          cursor: not-allowed;
          opacity: .55;
        }
        .title-actions :global(.cta-secondary:not([disabled]):hover) {
          border-color: rgba(217,167,58,.55);
          color: var(--ink-on-dark);
        }
        .title-actions :global(.cta-active) {
          text-decoration: none;
          color: var(--ink-on-dark);
        }
        .title-actions :global(.cta-active:hover) {
          border-color: rgba(217,167,58,.7);
          color: var(--card);
          transform: translateY(-2px);
          box-shadow: var(--shadow-md);
        }

        .title-footer {
          margin-top: 28px;
          font-family: var(--font-hand);
          font-size: 13px;
          color: rgba(248,236,210,.5);
          letter-spacing: .04em;
        }

        .sound-controls {
          position: absolute;
          top: max(16px, env(safe-area-inset-top));
          right: max(16px, env(safe-area-inset-right));
          z-index: 10;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .sound-toggle {
          width: 40px;
          height: 40px;
          display: grid;
          place-items: center;
          border-radius: 999px;
          border: var(--frame-gold);
          background: rgba(20,16,12,.55);
          backdrop-filter: blur(6px);
          color: var(--gold-soft);
          cursor: pointer;
          transition: transform .18s cubic-bezier(.22,.61,.36,1), color .18s, border-color .18s, box-shadow .18s;
        }
        .sound-toggle:hover {
          transform: translateY(-1px);
          color: var(--card);
          border-color: rgba(247,210,120,.9);
          box-shadow: var(--shadow-md);
        }
        .sound-toggle:focus-visible {
          outline: 2px solid rgba(247,210,120,.9);
          outline-offset: 2px;
        }

        .volume-slider {
          width: 96px;
          height: 40px;
          cursor: pointer;
          -webkit-appearance: none;
          appearance: none;
          background: transparent;
        }
        .volume-slider::-webkit-slider-runnable-track {
          height: 4px;
          border-radius: 999px;
          background: linear-gradient(90deg, var(--gold-soft), rgba(247,210,120,.25));
        }
        .volume-slider::-moz-range-track {
          height: 4px;
          border-radius: 999px;
          background: linear-gradient(90deg, var(--gold-soft), rgba(247,210,120,.25));
        }
        .volume-slider::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          margin-top: -6px;
          width: 16px;
          height: 16px;
          border-radius: 999px;
          background: var(--card);
          border: 2px solid rgba(247,210,120,.9);
          box-shadow: var(--shadow-sm);
        }
        .volume-slider::-moz-range-thumb {
          width: 16px;
          height: 16px;
          border-radius: 999px;
          background: var(--card);
          border: 2px solid rgba(247,210,120,.9);
          box-shadow: var(--shadow-sm);
        }
        .volume-slider:focus-visible {
          outline: 2px solid rgba(247,210,120,.9);
          outline-offset: 4px;
          border-radius: 999px;
        }
      `}</style>
    </main>
  );
}
