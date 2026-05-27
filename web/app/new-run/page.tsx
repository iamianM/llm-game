"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { listCheckpoints, newSession, sessionFromCheckpoint } from "../../lib/api";
import { rememberCurrentSession } from "../../lib/storage";
import type { CheckpointSummary, Gender } from "../../lib/types";
import { ArchetypeCard } from "../../components/chrome/ArchetypeCard";

const ARCHETYPES = [
  { id: "heartthrob", title: "Heartthrob", bonus: "+3 Charm", advantage: "Walk into Sunset Bay with instant spark." },
  { id: "class_clown", title: "Class Clown", bonus: "+3 Banter", advantage: "Quick jokes, warm timing, crowd-pleaser edge." },
  { id: "loyal_friend", title: "Loyal Friend", bonus: "+3 Loyalty", advantage: "Start with steadier bonds and a real reputation." }
];

export default function NewRunPage() {
  const [archetype, setArchetype] = useState("heartthrob");
  const [gender, setGender] = useState<Gender>("man");
  const [mockLlm, setMockLlm] = useState(false);
  const router = useRouter();
  const mutation = useMutation({
    mutationFn: () => newSession(archetype, gender, mockLlm),
    onSuccess: (data) => {
      rememberCurrentSession(data.session_id);
      router.push(`/play/${data.session_id}`);
    }
  });
  const checkpointMutation = useMutation({
    mutationFn: (name: string) => sessionFromCheckpoint(name, mockLlm),
    onSuccess: (data) => {
      rememberCurrentSession(data.session_id);
      router.push(`/play/${data.session_id}`);
    }
  });
  const checkpointQuery = useQuery({
    queryKey: ["checkpoints"],
    queryFn: listCheckpoints,
    staleTime: 60_000
  });
  const checkpoints: CheckpointSummary[] = checkpointQuery.data ?? [];

  if (mutation.isPending || checkpointMutation.isPending) {
    return <CastingLoader mockLlm={mockLlm} />;
  }

  return (
    <main className="newrun-stage film-grain vignette" data-screen="new-run">
      <div className="newrun-bg" aria-hidden />
      <div className="newrun-content">
        <header className="newrun-header">
          <p className="newrun-eyebrow flourish">Paradise Hearts · Casting</p>
          <h1 className="newrun-title">
            <span className="title-main gold-shimmer">Choose your opening vibe</span>
          </h1>
        </header>

        <div className="archetypes">
          {ARCHETYPES.map((item) => (
            <ArchetypeCard key={item.id} {...item} selected={archetype === item.id} onSelect={() => setArchetype(item.id)} />
          ))}
        </div>

        <div className="config-row">
          <section className="config-card">
            <span className="config-label">You walk in as</span>
            <div className="toggle-group">
              <Toggle on={gender === "man"} onClick={() => setGender("man")}>Man</Toggle>
              <Toggle on={gender === "woman"} onClick={() => setGender("woman")}>Woman</Toggle>
            </div>
          </section>

          <section className="config-card">
            <span className="config-label">Story engine</span>
            <div className="toggle-group">
              <Toggle on={mockLlm} onClick={() => setMockLlm(true)}>Test mode</Toggle>
              <Toggle on={!mockLlm} onClick={() => setMockLlm(false)}>Real mode</Toggle>
            </div>
          </section>

          <button
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
            className="enter-cta"
          >
            <span className="cta-label">{mutation.isPending ? "Opening…" : "Step into Sunset Bay"}</span>
            <span className="cta-arrow">→</span>
          </button>
        </div>

        {mutation.error ? (
          <p role="alert" className="error-banner">{mutation.error.message}</p>
        ) : null}
        {checkpointMutation.error ? (
          <p role="alert" className="error-banner">{checkpointMutation.error.message}</p>
        ) : null}

        {checkpoints.length > 0 ? (
          <section className="checkpoint-block" aria-label="Resume from a saved point">
            <header className="checkpoint-header">
              <span className="checkpoint-eyebrow">Or jump back in</span>
              <span className="checkpoint-sub">Resume from a saved point</span>
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
                  <span className="checkpoint-day">Day {ck.day} · {ck.phase}</span>
                  <span className="checkpoint-label">{ck.label}</span>
                  <span className="checkpoint-source">{ck.source === "bundled" ? "Demo" : "Local"}</span>
                </button>
              ))}
            </div>
          </section>
        ) : null}
      </div>

      <style jsx>{`
        .newrun-stage {
          position: relative;
          height: 100vh;
          height: 100svh;
          overflow: hidden;
          padding: 3vh 3vw;
          color: var(--ink-on-dark);
          isolation: isolate;
        }
        .newrun-bg {
          position: absolute; inset: 0;
          background:
            radial-gradient(100% 70% at 50% -10%, rgba(212,99,62,.22), transparent 50%),
            radial-gradient(80% 60% at 10% 100%, rgba(91,124,79,.18), transparent 60%),
            radial-gradient(80% 60% at 90% 100%, rgba(120,80,40,.20), transparent 60%),
            linear-gradient(180deg, #100b08, #060403);
          z-index: 0;
        }
        .newrun-content {
          position: relative; z-index: 3;
          max-width: 1200px;
          height: 100%;
          margin: 0 auto;
          display: grid;
          grid-template-rows: auto 1fr auto;
          gap: 18px;
        }
        .newrun-header {
          text-align: center;
        }
        .newrun-eyebrow {
          font-family: var(--font-hand);
          color: var(--gold-soft);
          font-size: 15px;
          letter-spacing: .04em;
          margin-bottom: 8px;
        }
        .newrun-title { margin: 0; font-family: var(--font-display); font-weight: 600; line-height: 1; }
        .title-main {
          display: block;
          font-style: italic;
          font-size: clamp(34px, 5.2vw, 64px);
          letter-spacing: -.02em;
        }

        .archetypes {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 14px;
          align-content: center;
          min-height: 0;
        }
        @media (max-width: 760px) {
          .archetypes { grid-template-columns: 1fr; gap: 8px; }
        }

        .config-row {
          display: grid;
          grid-template-columns: 1fr 1fr auto;
          gap: 14px;
          align-items: center;
        }
        @media (max-width: 760px) {
          .config-row { grid-template-columns: 1fr; gap: 10px; }
        }
        .config-card {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 14px;
          border-radius: var(--r-lg);
          border: var(--frame-gold);
          background: rgba(20,16,12,.6);
          backdrop-filter: blur(8px);
        }
        .config-label {
          font-size: 10px;
          letter-spacing: .14em;
          text-transform: uppercase;
          font-weight: 700;
          color: var(--gold-soft);
          flex-shrink: 0;
        }
        .toggle-group {
          display: inline-flex;
          gap: 4px;
          padding: 3px;
          border-radius: var(--r-pill);
          background: rgba(0,0,0,.4);
          border: 1px solid rgba(248,236,210,.08);
          margin-left: auto;
        }

        .enter-cta {
          display: inline-flex;
          align-items: center;
          gap: 12px;
          padding: 14px 26px;
          font-family: var(--font-display);
          font-size: 18px;
          font-style: italic;
          color: var(--card);
          background: linear-gradient(180deg, var(--accent), var(--accent-deep));
          border: 1px solid rgba(217,167,58,.55);
          border-radius: var(--r-pill);
          cursor: pointer;
          box-shadow: var(--shadow-lg), var(--inset-gold);
          transition: transform .18s, box-shadow .18s;
          white-space: nowrap;
        }
        .enter-cta:hover:not([disabled]) { transform: translateY(-2px); box-shadow: var(--shadow-lg), var(--shadow-accent), var(--inset-gold); }
        .enter-cta[disabled] { opacity: .55; cursor: progress; }
        .cta-arrow { font-size: 20px; font-style: normal; transition: transform .2s; }
        .enter-cta:hover:not([disabled]) .cta-arrow { transform: translateX(4px); }

        .error-banner {
          position: absolute;
          left: 50%; bottom: 14px; transform: translateX(-50%);
          padding: 8px 14px;
          border-radius: var(--r-md);
          background: rgba(193,75,58,.18);
          border: 1px solid rgba(193,75,58,.45);
          color: #f7c8c1;
          font-size: 13px;
        }

        .checkpoint-block {
          margin-top: 14px;
          padding: 12px 14px;
          border-radius: var(--r-lg);
          border: var(--frame-gold);
          background: rgba(20,16,12,.55);
          backdrop-filter: blur(8px);
        }
        .checkpoint-header {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 10px;
        }
        .checkpoint-eyebrow {
          font-family: var(--font-hand);
          color: var(--gold-soft);
          font-size: 14px;
          letter-spacing: .04em;
        }
        .checkpoint-sub {
          font-size: 12px;
          color: var(--ink-on-dark);
          opacity: .65;
        }
        .checkpoint-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
          gap: 8px;
        }
        .checkpoint-card {
          display: flex;
          flex-direction: column;
          gap: 4px;
          padding: 10px 12px;
          text-align: left;
          cursor: pointer;
          background: rgba(36,28,22,.55);
          color: var(--ink-on-dark);
          border: 1px solid rgba(212,166,99,.25);
          border-radius: var(--r-md);
          transition: transform .12s, border-color .12s, background .12s;
        }
        .checkpoint-card:hover:not([disabled]) {
          transform: translateY(-1px);
          border-color: rgba(212,166,99,.6);
          background: rgba(48,36,28,.65);
        }
        .checkpoint-card[disabled] { opacity: .55; cursor: progress; }
        .checkpoint-card.bundled { border-color: rgba(212,166,99,.4); }
        .checkpoint-day {
          font-family: var(--font-hand);
          font-size: 13px;
          color: var(--gold-soft);
          letter-spacing: .03em;
          text-transform: uppercase;
        }
        .checkpoint-label {
          font-size: 14px;
          font-weight: 500;
        }
        .checkpoint-source {
          font-size: 11px;
          color: var(--ink-on-dark);
          opacity: .5;
        }
      `}</style>
    </main>
  );
}

function CastingLoader({ mockLlm }: { mockLlm: boolean }) {
  const beats = mockLlm
    ? ["Calling places…", "Mixing the cast…", "Lighting the firepit…"]
    : ["Casting your Heartbreakers…", "Writing their backstories…", "Setting the scene at Sunset Bay…"];
  return (
    <main className="loader-stage film-grain vignette" data-screen="casting-loader">
      <div className="loader-bg" aria-hidden />
      <div className="loader-content">
        <p className="loader-eyebrow flourish">Paradise Hearts</p>
        <h1 className="loader-title gold-shimmer">Opening Sunset Bay</h1>
        <div className="loader-spinner" aria-hidden>
          <span /><span /><span />
        </div>
        <ul className="loader-beats">
          {beats.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </div>

      <style jsx>{`
        .loader-stage {
          position: relative;
          height: 100vh;
          height: 100svh;
          overflow: hidden;
          color: var(--ink-on-dark);
          isolation: isolate;
          display: grid;
          place-items: center;
        }
        .loader-bg {
          position: absolute; inset: 0;
          background:
            radial-gradient(100% 70% at 50% -10%, rgba(212,99,62,.28), transparent 55%),
            radial-gradient(80% 60% at 10% 100%, rgba(91,124,79,.22), transparent 60%),
            radial-gradient(80% 60% at 90% 100%, rgba(120,80,40,.24), transparent 60%),
            linear-gradient(180deg, #100b08, #060403);
          z-index: 0;
        }
        .loader-content {
          position: relative;
          z-index: 1;
          display: grid;
          gap: 22px;
          place-items: center;
          padding: 0 32px;
          text-align: center;
        }
        .loader-eyebrow {
          font-family: var(--font-hand);
          font-size: 16px;
          color: var(--gold-soft);
          letter-spacing: .04em;
          opacity: .9;
          margin: 0;
        }
        .loader-title {
          margin: 0;
          font-family: var(--font-display);
          font-weight: 600;
          font-style: italic;
          font-size: clamp(36px, 6vw, 64px);
          letter-spacing: -.02em;
        }
        .loader-spinner {
          display: inline-flex;
          gap: 8px;
        }
        .loader-spinner span {
          width: 10px; height: 10px;
          border-radius: 50%;
          background: var(--gold-soft);
          box-shadow: 0 0 12px rgba(217,167,58,.55);
          animation: loader-pulse 1.2s ease-in-out infinite;
        }
        .loader-spinner span:nth-child(2) { animation-delay: .15s; }
        .loader-spinner span:nth-child(3) { animation-delay: .3s; }
        @keyframes loader-pulse {
          0%, 80%, 100% { transform: scale(0.6); opacity: .5; }
          40% { transform: scale(1); opacity: 1; }
        }
        .loader-beats {
          margin: 6px 0 0;
          padding: 0;
          list-style: none;
          display: grid;
          gap: 4px;
          color: var(--muted-on-dark);
          font-size: 13.5px;
          font-style: italic;
          font-family: var(--font-display);
          letter-spacing: .02em;
          max-width: 36ch;
        }
      `}</style>
    </main>
  );
}

function Toggle({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={`toggle-pill ${on ? "is-on" : ""}`}
    >
      {children}
      <style jsx>{`
        .toggle-pill {
          padding: 6px 14px;
          border-radius: var(--r-pill);
          border: 0;
          background: transparent;
          color: var(--muted-on-dark);
          font-size: 12.5px;
          font-weight: 500;
          cursor: pointer;
          transition: background .15s, color .15s;
        }
        .toggle-pill:hover { color: var(--ink-on-dark); }
        .toggle-pill.is-on {
          background: linear-gradient(180deg, var(--accent), var(--accent-deep));
          color: var(--card);
          box-shadow: var(--shadow-sm), var(--inset-gold);
        }
      `}</style>
    </button>
  );
}
