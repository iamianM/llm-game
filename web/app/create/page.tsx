"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { listCheckpoints, newSession, sessionFromCheckpoint } from "../../lib/api";
import { rememberCurrentSession } from "../../lib/storage";
import { DEFAULT_USE_LIVE_LLM, useUiStore } from "../../lib/store";
import type { CheckpointSummary } from "../../lib/types";
import { LookStage } from "../../components/look/LookStage";
import { commitDraftToSession, findArchetype, findVibe, loadDraftLook, saveDraftLook } from "../../lib/look";
import { ROSTER, findRosterCharacter, isRosterId, rosterLook } from "../../lib/roster";

export default function CreatePage() {
  const router = useRouter();
  const [selectedId, setSelectedId] = useState<string>(ROSTER[0].id);
  const [checkpointOpen, setCheckpointOpen] = useState(false);

  const useLive = useUiStore((s) => s.useLiveLlm);
  const setUseLive = useUiStore((s) => s.setUseLiveLlm);
  const mockLlm = !useLive;

  // Restore the last picked islander and sync the engine toggle from storage.
  useEffect(() => {
    const draft = loadDraftLook();
    if (isRosterId(draft.characterId)) setSelectedId(draft.characterId as string);
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem("paradise.settings.useLiveLlm");
    if (stored === "1" && !useLive) setUseLive(true);
    if (stored === "0" && useLive) setUseLive(false);
    if (stored === null && DEFAULT_USE_LIVE_LLM && !useLive) setUseLive(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selected = findRosterCharacter(selectedId) ?? ROSTER[0];
  const look = useMemo(() => rosterLook(selected), [selected]);

  // Persist the pick so a refresh keeps it selected.
  useEffect(() => {
    saveDraftLook(look);
  }, [look]);

  const mutation = useMutation({
    mutationFn: () => newSession(selected.archetype, selected.gender, mockLlm, selected.name),
    onSuccess: (data) => {
      commitDraftToSession(data.session_id, look);
      rememberCurrentSession(data.session_id);
      router.push(`/play/${data.session_id}`);
    },
  });

  const checkpointMutation = useMutation({
    mutationFn: (name: string) => sessionFromCheckpoint(name, mockLlm),
    onSuccess: (data) => {
      rememberCurrentSession(data.session_id);
      router.push(`/play/${data.session_id}`);
    },
  });

  const checkpointQuery = useQuery({ queryKey: ["checkpoints"], queryFn: listCheckpoints, staleTime: 60_000 });
  const checkpoints: CheckpointSummary[] = checkpointQuery.data ?? [];

  if (mutation.isPending || checkpointMutation.isPending) {
    return <CastingLoader mockLlm={mockLlm} />;
  }

  const archetype = findArchetype(selected.archetype);

  return (
    <main className="select-page film-grain vignette" data-screen="create">
      <div className="select-bg" aria-hidden />

      <header className="select-topbar">
        <Link href="/" className="icon-link" aria-label="Back to title">
          <ArrowLeft size={18} />
        </Link>
        <div className="topbar-title">
          <p className="kicker flourish">Paradise Hearts / Casting</p>
          <h1>Choose your Islander</h1>
        </div>
      </header>

      <section className="select-layout">
        {/* ROSTER GRID */}
        <div className="roster-grid" role="radiogroup" aria-label="Playable islanders" data-testid="roster-grid">
          {ROSTER.map((character) => {
            const on = character.id === selected.id;
            return (
              <button
                key={character.id}
                type="button"
                role="radio"
                aria-checked={on}
                data-character-id={character.id}
                className={`roster-card${on ? " is-on" : ""}`}
                onClick={() => setSelectedId(character.id)}
              >
                <span className="roster-stage">
                  <LookStage look={rosterLook(character)} compact />
                </span>
                <span className="roster-meta">
                  <b>{character.name}</b>
                  <small>{findArchetype(character.archetype).label}</small>
                </span>
              </button>
            );
          })}
        </div>

        {/* PREVIEW + ACTIONS */}
        <section className="preview-zone" aria-label="Selected islander">
          <div className="casting-card" data-testid="selected-preview">
            <LookStage look={look} />
            <div className="nameplate">
              <span className="nameplate-name">{selected.name}</span>
              <span className="nameplate-sub">{archetype.label} · {findVibe(selected.vibe).label}</span>
            </div>
          </div>

          <div className="preview-actions">
            <p className="tagline">{selected.tagline}</p>
            <p className="bonus-line">{archetype.bonus} · {archetype.detail}</p>
            <div className="engine-row">
              <span className="engine-label">Story engine</span>
              <div className="seg">
                <SegButton on={!useLive} onClick={() => setUseLive(false)}>Demo</SegButton>
                <SegButton on={useLive} onClick={() => setUseLive(true)}>Live LLM</SegButton>
              </div>
            </div>
            <button type="button" className="enter-cta" disabled={mutation.isPending} onClick={() => mutation.mutate()}>
              <span className="cta-label">Play as {selected.name}</span>
              <span className="cta-arrow" aria-hidden>→</span>
            </button>
            {checkpoints.length > 0 ? (
              <button type="button" className="ghost-cta" onClick={() => setCheckpointOpen(true)}>
                Resume from checkpoint
              </button>
            ) : null}
          </div>
          {mutation.error ? <p role="alert" className="error-banner">{mutation.error.message}</p> : null}
          {checkpointMutation.error ? <p role="alert" className="error-banner">{checkpointMutation.error.message}</p> : null}
        </section>
      </section>

      {checkpointOpen && checkpoints.length > 0 ? (
        <div className="checkpoint-overlay" role="dialog" aria-modal="true" aria-label="Resume from checkpoint">
          <div className="checkpoint-sheet">
            <header className="sheet-header">
              <div>
                <span className="kicker">Jump into the villa</span>
                <h2 className="sheet-title">Choose a checkpoint</h2>
              </div>
              <button type="button" className="sheet-close" onClick={() => setCheckpointOpen(false)}>Close</button>
            </header>
            <div className="checkpoint-grid">
              {checkpoints.map((ck) => (
                <button
                  key={ck.name}
                  className={`checkpoint-card${ck.source === "bundled" ? " bundled" : ""}`}
                  onClick={() => checkpointMutation.mutate(ck.name)}
                  disabled={checkpointMutation.isPending}
                  type="button"
                >
                  <span className="checkpoint-day">Day {ck.day} / {ck.phase}</span>
                  <span className="checkpoint-label">{ck.label}</span>
                  <span className="checkpoint-source">{ck.source === "bundled" ? "Demo" : "Local"}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      <style jsx>{`
        .select-page {
          position: relative;
          min-height: 100vh;
          min-height: 100svh;
          color: var(--ink-on-dark);
          padding: 14px;
          isolation: isolate;
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .select-bg {
          position: absolute;
          inset: 0;
          z-index: 0;
          background:
            radial-gradient(80% 64% at 18% -12%, rgba(21, 138, 147, .30), transparent 58%),
            radial-gradient(78% 70% at 84% -10%, rgba(212, 99, 62, .34), transparent 60%),
            radial-gradient(74% 64% at 52% 116%, rgba(111, 76, 160, .22), transparent 62%),
            linear-gradient(180deg, #160c09 0%, #070504 100%);
        }
        .select-topbar,
        .select-layout {
          position: relative;
          z-index: 2;
          width: 100%;
          max-width: 1280px;
        }
        .select-topbar {
          min-height: 64px;
          display: grid;
          grid-template-columns: 42px 1fr;
          align-items: center;
          gap: 12px;
          margin-bottom: 12px;
        }
        .topbar-title h1 {
          margin: 0;
          font-family: var(--font-display);
          font-style: italic;
          font-size: clamp(26px, 4vw, 46px);
          line-height: 1;
          color: var(--card);
        }
        .kicker {
          margin: 0 0 3px;
          color: var(--gold-soft);
          font-size: 11px;
          font-weight: 800;
          letter-spacing: .14em;
          text-transform: uppercase;
        }
        .select-topbar :global(.icon-link) {
          width: 42px;
          height: 42px;
          border-radius: 50%;
          border: var(--frame-gold);
          color: var(--ink-on-dark);
          background: rgba(20, 16, 12, .72);
          display: inline-flex;
          align-items: center;
          justify-content: center;
          text-decoration: none;
        }
        .select-layout {
          display: grid;
          grid-template-columns: minmax(340px, 1fr) minmax(300px, 420px);
          gap: 16px;
          flex: 1;
          min-height: 0;
        }
        .roster-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
          align-content: start;
        }
        .roster-card {
          position: relative;
          display: grid;
          grid-template-rows: 1fr auto;
          aspect-ratio: 3 / 4;
          border-radius: var(--r-lg);
          overflow: hidden;
          border: 1px solid rgba(248, 236, 210, .14);
          background: rgba(13, 10, 9, .6);
          cursor: pointer;
          transition: transform .14s, border-color .14s, box-shadow .14s;
        }
        .roster-card:hover { transform: translateY(-2px); }
        .roster-card.is-on {
          border-color: rgba(217, 167, 58, .8);
          box-shadow: 0 0 0 2px rgba(217, 167, 58, .26), var(--shadow-lg);
        }
        .roster-stage { position: relative; }
        .roster-meta {
          display: grid;
          gap: 1px;
          padding: 8px 10px;
          background: rgba(8, 6, 4, .72);
          text-align: left;
        }
        .roster-meta b { font-family: var(--font-display); font-size: 16px; color: var(--card); }
        .roster-meta small { font-size: 10px; letter-spacing: .12em; text-transform: uppercase; color: var(--gold-soft); }

        .preview-zone {
          min-height: 0;
          display: grid;
          grid-template-rows: minmax(0, 1fr) auto;
          gap: 12px;
        }
        .casting-card {
          position: relative;
          min-height: 320px;
          border: var(--frame-gold);
          border-radius: var(--r-xl);
          overflow: hidden;
          box-shadow: var(--shadow-lg), var(--inset-gold);
          background: rgba(13, 10, 9, .6);
        }
        .nameplate {
          position: absolute;
          left: 50%;
          bottom: 14px;
          transform: translateX(-50%);
          z-index: 4;
          display: grid;
          justify-items: center;
          gap: 2px;
          padding: 7px 18px;
          border-radius: var(--r-pill);
          background: rgba(8, 6, 4, .68);
          border: 1px solid rgba(217, 167, 58, .35);
          backdrop-filter: blur(6px);
          text-align: center;
          max-width: 86%;
        }
        .nameplate-name {
          font-family: var(--font-display);
          font-size: clamp(18px, 2.6vw, 26px);
          line-height: 1;
          color: var(--card);
        }
        .nameplate-sub {
          font-size: 10px;
          letter-spacing: .14em;
          text-transform: uppercase;
          color: var(--gold-soft);
        }
        .preview-actions { display: grid; gap: 10px; }
        .tagline { margin: 0; font-size: 14px; line-height: 1.4; color: var(--ink-on-dark); }
        .bonus-line { margin: 0; font-size: 12px; color: var(--muted-on-dark); }
        .engine-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          padding: 8px 12px;
          border-radius: var(--r-md);
          border: var(--frame-gold);
          background: rgba(20, 16, 12, .6);
        }
        .engine-label { font-size: 10px; letter-spacing: .14em; text-transform: uppercase; font-weight: 800; color: var(--gold-soft); }
        .seg {
          display: inline-flex;
          gap: 4px;
          padding: 3px;
          border-radius: var(--r-pill);
          background: rgba(0, 0, 0, .4);
          border: 1px solid rgba(248, 236, 210, .08);
        }
        .enter-cta {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          min-height: 52px;
          padding: 13px 24px;
          font-family: var(--font-display);
          font-size: 19px;
          font-style: italic;
          color: var(--card);
          background: linear-gradient(180deg, var(--accent), var(--accent-deep));
          border: 1px solid rgba(217, 167, 58, .55);
          border-radius: var(--r-pill);
          cursor: pointer;
          box-shadow: var(--shadow-lg), var(--inset-gold);
          transition: transform .18s, box-shadow .18s;
        }
        .enter-cta:hover:not([disabled]) { transform: translateY(-2px); box-shadow: var(--shadow-lg), var(--shadow-accent), var(--inset-gold); }
        .enter-cta[disabled] { opacity: .55; cursor: progress; }
        .cta-arrow { font-size: 21px; font-style: normal; transition: transform .2s; }
        .enter-cta:hover:not([disabled]) .cta-arrow { transform: translateX(4px); }
        .ghost-cta {
          min-height: 42px;
          border-radius: var(--r-pill);
          border: 1px solid rgba(217, 167, 58, .38);
          background: rgba(20, 16, 12, .64);
          color: var(--gold-soft);
          font-size: 12px;
          font-weight: 700;
          letter-spacing: .1em;
          text-transform: uppercase;
          cursor: pointer;
        }
        .error-banner {
          margin: 0;
          padding: 8px 14px;
          border-radius: var(--r-md);
          background: rgba(193, 75, 58, .18);
          border: 1px solid rgba(193, 75, 58, .45);
          color: #f7c8c1;
          font-size: 13px;
        }

        .checkpoint-overlay {
          position: fixed;
          inset: 0;
          z-index: 20;
          display: grid;
          place-items: end center;
          padding: 14px;
          background: rgba(5, 3, 2, .68);
          backdrop-filter: blur(8px);
        }
        .checkpoint-sheet {
          width: min(720px, 100%);
          max-height: min(80vh, 660px);
          display: grid;
          grid-template-rows: auto minmax(0, 1fr);
          gap: 12px;
          padding: 14px;
          border-radius: var(--r-xl);
          border: var(--frame-gold);
          background: linear-gradient(180deg, rgba(20, 16, 12, .96), rgba(8, 6, 4, .98));
          box-shadow: var(--shadow-lg), var(--inset-gold);
        }
        .sheet-header { display: flex; align-items: start; justify-content: space-between; gap: 12px; }
        .sheet-title { margin: 2px 0 0; font-family: var(--font-display); font-size: 26px; color: var(--ink-on-dark); }
        .sheet-close {
          min-height: 36px;
          padding: 8px 13px;
          border-radius: var(--r-pill);
          border: 1px solid rgba(248, 236, 210, .14);
          background: rgba(248, 236, 210, .06);
          color: var(--ink-on-dark);
          font-size: 12px;
          font-weight: 700;
          letter-spacing: .08em;
          text-transform: uppercase;
          cursor: pointer;
        }
        .checkpoint-grid {
          overflow-y: auto;
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
          gap: 8px;
          padding-right: 2px;
        }
        .checkpoint-card {
          display: flex;
          flex-direction: column;
          gap: 4px;
          padding: 10px 12px;
          text-align: left;
          cursor: pointer;
          background: rgba(36, 28, 22, .55);
          color: var(--ink-on-dark);
          border: 1px solid rgba(212, 166, 99, .25);
          border-radius: var(--r-md);
        }
        .checkpoint-card[disabled] { opacity: .55; cursor: progress; }
        .checkpoint-day { font-family: var(--font-hand); font-size: 13px; color: var(--gold-soft); text-transform: uppercase; }
        .checkpoint-label { font-size: 14px; }
        .checkpoint-source { font-size: 11px; opacity: .5; }

        @media (max-width: 880px) {
          .select-layout { grid-template-columns: 1fr; }
          .preview-zone { order: 1; }
          .roster-grid { order: 2; }
          .casting-card { min-height: 360px; }
          .checkpoint-grid { grid-template-columns: 1fr; }
        }
      `}</style>
    </main>
  );
}

function SegButton({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" aria-pressed={on} onClick={onClick} className={`seg-pill${on ? " is-on" : ""}`}>
      {children}
      <style jsx>{`
        .seg-pill {
          padding: 7px 16px;
          border-radius: var(--r-pill);
          border: 0;
          background: transparent;
          color: var(--muted-on-dark);
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
        }
        .seg-pill.is-on {
          background: linear-gradient(180deg, var(--accent), var(--accent-deep));
          color: var(--card);
          box-shadow: var(--shadow-sm), var(--inset-gold);
        }
      `}</style>
    </button>
  );
}

function CastingLoader({ mockLlm }: { mockLlm: boolean }) {
  const beats = mockLlm
    ? ["Calling places…", "Mixing the cast…", "Lighting the firepit…"]
    : ["Casting your Islanders…", "Writing their backstories…", "Setting the scene at Sunset Bay…"];
  return (
    <main className="loader-stage film-grain vignette" data-screen="casting-loader">
      <div className="loader-bg" aria-hidden />
      <div className="loader-content">
        <p className="loader-eyebrow flourish">Paradise Hearts</p>
        <h1 className="loader-title gold-shimmer">Opening Sunset Bay</h1>
        <div className="loader-spinner" aria-hidden><span /><span /><span /></div>
        <ul className="loader-beats">{beats.map((line) => <li key={line}>{line}</li>)}</ul>
      </div>
      <style jsx>{`
        .loader-stage { position: relative; height: 100vh; height: 100svh; overflow: hidden; color: var(--ink-on-dark); display: grid; place-items: center; isolation: isolate; }
        .loader-bg {
          position: absolute; inset: 0; z-index: 0;
          background:
            radial-gradient(100% 70% at 50% -10%, rgba(212, 99, 62, .28), transparent 55%),
            radial-gradient(80% 60% at 10% 100%, rgba(91, 124, 79, .22), transparent 60%),
            linear-gradient(180deg, #100b08, #060403);
        }
        .loader-content { position: relative; z-index: 1; display: grid; gap: 20px; place-items: center; text-align: center; padding: 0 28px; }
        .loader-eyebrow { font-family: var(--font-hand); font-size: 16px; color: var(--gold-soft); margin: 0; }
        .loader-title { margin: 0; font-family: var(--font-display); font-style: italic; font-size: clamp(34px, 6vw, 60px); }
        .loader-spinner { display: inline-flex; gap: 8px; }
        .loader-spinner span { width: 10px; height: 10px; border-radius: 50%; background: var(--gold-soft); box-shadow: 0 0 12px rgba(217, 167, 58, .55); animation: loader-pulse 1.2s ease-in-out infinite; }
        .loader-spinner span:nth-child(2) { animation-delay: .15s; }
        .loader-spinner span:nth-child(3) { animation-delay: .3s; }
        @keyframes loader-pulse { 0%, 80%, 100% { transform: scale(.6); opacity: .5; } 40% { transform: scale(1); opacity: 1; } }
        .loader-beats { margin: 4px 0 0; padding: 0; list-style: none; display: grid; gap: 4px; color: var(--muted-on-dark); font-size: 13.5px; font-style: italic; font-family: var(--font-display); }
      `}</style>
    </main>
  );
}
