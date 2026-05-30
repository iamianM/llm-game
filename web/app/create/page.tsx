"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Check, Dice5, Shuffle, Sparkles } from "lucide-react";
import { listCheckpoints, newSession, sessionFromCheckpoint } from "../../lib/api";
import { rememberCurrentSession } from "../../lib/storage";
import { DEFAULT_USE_LIVE_LLM, useUiStore } from "../../lib/store";
import type { CheckpointSummary, Gender } from "../../lib/types";
import { AccessoryBadges } from "../../components/chrome/AccessoryBadges";
import { LookStage } from "../../components/look/LookStage";
import {
  ACCESSORIES,
  ARCHETYPES,
  HAIR_COLORS,
  OUTFITS,
  SKIN_TONES,
  VIBES,
  DEFAULT_LOOK,
  commitDraftToSession,
  findArchetype,
  findHairColor,
  findOutfit,
  findSkinTone,
  findVibe,
  loadDraftLook,
  saveDraftLook,
  type IslanderLook,
} from "../../lib/look";

type Section = "islander" | "look" | "wardrobe";

export default function CreatePage() {
  const router = useRouter();
  const [look, setLook] = useState<IslanderLook>(DEFAULT_LOOK);
  const [section, setSection] = useState<Section>("islander");
  const [checkpointOpen, setCheckpointOpen] = useState(false);

  const useLive = useUiStore((s) => s.useLiveLlm);
  const setUseLive = useUiStore((s) => s.setUseLiveLlm);
  const mockLlm = !useLive;

  // Restore the in-progress draft and sync the engine toggle from storage.
  useEffect(() => {
    setLook(loadDraftLook());
    if (typeof window === "undefined") return;
    const stored = window.localStorage.getItem("paradise.settings.useLiveLlm");
    if (stored === "1" && !useLive) setUseLive(true);
    if (stored === "0" && useLive) setUseLive(false);
    if (stored === null && DEFAULT_USE_LIVE_LLM && !useLive) setUseLive(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist the draft as the user styles so a refresh keeps their work.
  useEffect(() => {
    saveDraftLook(look);
  }, [look]);

  const update = <K extends keyof IslanderLook>(key: K, value: IslanderLook[K]) =>
    setLook((cur) => ({ ...cur, [key]: value }));

  const toggleAccessory = (id: string) =>
    setLook((cur) => ({
      ...cur,
      accessories: cur.accessories.includes(id)
        ? cur.accessories.filter((a) => a !== id)
        : [...cur.accessories, id].slice(0, 8),
    }));

  const shuffle = () =>
    setLook((cur) => ({
      ...cur,
      skinTone: pick(SKIN_TONES).id,
      hairColor: pick(HAIR_COLORS).id,
      outfit: pick(OUTFITS).id,
      vibe: pick(VIBES).id,
      accessories: ACCESSORIES.filter(() => Math.random() < 0.3)
        .slice(0, 3)
        .map((a) => a.id),
    }));

  const mutation = useMutation({
    mutationFn: () => newSession(look.archetype, look.gender, mockLlm, look.name),
    onSuccess: (data) => {
      const named: IslanderLook = { ...look, name: (look.name || "").trim() };
      commitDraftToSession(data.session_id, named);
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

  const archetype = findArchetype(look.archetype);
  const outfit = findOutfit(look.outfit);

  return (
    <main className="creator-page film-grain vignette" data-screen="create">
      <div className="creator-bg" aria-hidden />

      <header className="creator-topbar">
        <Link href="/" className="icon-link" aria-label="Back to title">
          <ArrowLeft size={18} />
        </Link>
        <div className="topbar-title">
          <p className="kicker flourish">Paradise Hearts / Casting</p>
          <h1>Create your Islander</h1>
        </div>
        <button type="button" className="top-action" onClick={shuffle} aria-label="Shuffle look">
          <Shuffle size={16} />
          <span>Shuffle</span>
        </button>
      </header>

      <section className="creator-layout">
        {/* CONTROLS */}
        <aside className="panel controls" aria-label="Islander editor">
          <div className="tabs" role="tablist" aria-label="Editor sections">
            <TabButton active={section === "islander"} onClick={() => setSection("islander")}>Islander</TabButton>
            <TabButton active={section === "look"} onClick={() => setSection("look")}>Look</TabButton>
            <TabButton active={section === "wardrobe"} onClick={() => setSection("wardrobe")}>Wardrobe</TabButton>
          </div>

          <div className="control-scroll">
            {section === "islander" ? (
              <div className="stack">
                <Field label="Name">
                  <input
                    className="name-input"
                    value={look.name}
                    maxLength={18}
                    placeholder="Your islander"
                    aria-label="Islander name"
                    onChange={(e) => update("name", e.target.value)}
                  />
                </Field>
                <Field label="You walk in as">
                  <div className="seg">
                    <SegButton on={look.gender === "man"} onClick={() => update("gender", "man" as Gender)}>Man</SegButton>
                    <SegButton on={look.gender === "woman"} onClick={() => update("gender", "woman" as Gender)}>Woman</SegButton>
                  </div>
                </Field>
                <Field label="Your type">
                  <div className="card-options" data-testid="archetype-options">
                    {ARCHETYPES.map((a) => (
                      <button
                        key={a.id}
                        type="button"
                        role="tab"
                        aria-selected={look.archetype === a.id}
                        className={`big-card${look.archetype === a.id ? " is-on" : ""}`}
                        onClick={() => update("archetype", a.id)}
                      >
                        <span className="big-card-head">
                          <b>{a.label}</b>
                          <span className="badge">{a.bonus}</span>
                        </span>
                        <small>{a.detail}</small>
                        {look.archetype === a.id ? <Check className="card-check" size={16} /> : null}
                      </button>
                    ))}
                  </div>
                </Field>
              </div>
            ) : null}

            {section === "look" ? (
              <div className="stack">
                <SwatchField title="Skin tone" options={SKIN_TONES} value={look.skinTone} onChange={(id) => update("skinTone", id)} />
                <SwatchField title="Hair colour" options={HAIR_COLORS} value={look.hairColor} onChange={(id) => update("hairColor", id)} />
                <SwatchField title="Energy" options={VIBES} value={look.vibe} onChange={(id) => update("vibe", id)} labelled />
              </div>
            ) : null}

            {section === "wardrobe" ? (
              <div className="stack">
                <Field label="Outfit">
                  <div className="outfit-options">
                    {OUTFITS.map((o) => (
                      <button
                        key={o.id}
                        type="button"
                        className={`outfit-row${look.outfit === o.id ? " is-on" : ""}`}
                        onClick={() => update("outfit", o.id)}
                      >
                        <span className="outfit-swatch" style={{ background: `linear-gradient(135deg, ${o.primary}, ${o.secondary})` }} />
                        <span className="outfit-meta">
                          <b>{o.label}</b>
                          <small>{o.detail}</small>
                        </span>
                        {look.outfit === o.id ? <Check size={16} /> : null}
                      </button>
                    ))}
                  </div>
                </Field>
                <Field label={`Accessories (${look.accessories.length})`}>
                  <div className="chip-grid" data-testid="accessory-grid">
                    {ACCESSORIES.map((a) => {
                      const on = look.accessories.includes(a.id);
                      return (
                        <button
                          key={a.id}
                          type="button"
                          aria-pressed={on}
                          className={`chip${on ? " is-on" : ""}`}
                          onClick={() => toggleAccessory(a.id)}
                        >
                          {a.label}
                        </button>
                      );
                    })}
                  </div>
                </Field>
              </div>
            ) : null}
          </div>
        </aside>

        {/* PREVIEW */}
        <section className="preview-zone" aria-label="Islander preview">
          <div className="casting-card" data-testid="avatar-preview">
            <LookStage look={look} />
            <div className="nameplate">
              <span className="nameplate-name">{look.name.trim() || "Your Islander"}</span>
              <span className="nameplate-sub">{archetype.label} · {findVibe(look.vibe).label}</span>
            </div>
            <div className="badge-rail">
              <AccessoryBadges ids={look.accessories} />
            </div>
          </div>

          <div className="preview-actions">
            <div className="engine-row">
              <span className="engine-label">Story engine</span>
              <div className="seg">
                <SegButton on={!useLive} onClick={() => setUseLive(false)}>Demo</SegButton>
                <SegButton on={useLive} onClick={() => setUseLive(true)}>Live LLM</SegButton>
              </div>
            </div>
            <button
              type="button"
              className="enter-cta"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate()}
            >
              <span className="cta-label">{mutation.isPending ? "Opening…" : "Step into Sunset Bay"}</span>
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

        {/* SUMMARY */}
        <aside className="panel summary" aria-label="Look summary">
          <div className="profile-card">
            <div className="mini-card">
              <LookStage look={look} compact />
            </div>
            <div>
              <p className="kicker">Draft Islander</p>
              <h2 className="profile-name">{look.name.trim() || "Your Islander"}</h2>
              <p className="profile-line">{archetype.label} · {outfit.label.toLowerCase()} styling</p>
            </div>
          </div>
          <SummaryRows
            rows={[
              ["Bonus", archetype.bonus],
              ["Skin", findSkinTone(look.skinTone).detail],
              ["Hair", findHairColor(look.hairColor).detail],
              ["Energy", findVibe(look.vibe).detail],
              ["Outfit", `${outfit.label} — ${outfit.category}`],
            ]}
          />
          <div className="acc-summary">
            <p className="panel-heading">Wearing</p>
            {look.accessories.length === 0 ? (
              <p className="acc-empty">Keeping it clean — no accessories yet.</p>
            ) : (
              <div className="acc-tags">
                {look.accessories.map((id) => {
                  const a = ACCESSORIES.find((x) => x.id === id);
                  return a ? <span className="acc-tag" key={id}>{a.label}</span> : null;
                })}
              </div>
            )}
          </div>
          <p className="reassure"><Sparkles size={13} /> You can change your look any time at the villa.</p>
        </aside>
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
        .creator-page {
          position: relative;
          height: 100vh;
          height: 100svh;
          color: var(--ink-on-dark);
          padding: 14px;
          isolation: isolate;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .creator-bg {
          position: absolute;
          inset: 0;
          z-index: 0;
          background:
            radial-gradient(80% 64% at 18% -12%, rgba(21, 138, 147, .30), transparent 58%),
            radial-gradient(78% 70% at 84% -10%, rgba(212, 99, 62, .34), transparent 60%),
            radial-gradient(74% 64% at 52% 116%, rgba(111, 76, 160, .22), transparent 62%),
            linear-gradient(180deg, #160c09 0%, #070504 100%);
        }
        .creator-topbar,
        .creator-layout {
          position: relative;
          z-index: 2;
          width: 100%;
          max-width: 1440px;
        }
        .creator-topbar {
          min-height: 64px;
          display: grid;
          grid-template-columns: 42px 1fr auto;
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
        .icon-link,
        .top-action {
          border: var(--frame-gold);
          color: var(--ink-on-dark);
          background: rgba(20, 16, 12, .72);
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 7px;
          cursor: pointer;
          text-decoration: none;
        }
        .icon-link { width: 42px; height: 42px; border-radius: 50%; }
        .top-action {
          min-height: 42px;
          padding: 8px 15px;
          border-radius: var(--r-pill);
          font-size: 12px;
          font-weight: 800;
          letter-spacing: .08em;
          text-transform: uppercase;
        }
        .creator-layout {
          display: grid;
          grid-template-columns: minmax(280px, 360px) minmax(340px, 1fr) minmax(260px, 340px);
          gap: 14px;
          align-items: stretch;
          flex: 1;
          min-height: 0;
        }
        .panel {
          border: var(--frame-gold);
          background: rgba(13, 10, 9, .80);
          box-shadow: var(--shadow-lg), var(--inset-gold);
          backdrop-filter: blur(12px);
          border-radius: var(--r-xl);
          padding: 12px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          min-height: 0;
        }
        .tabs {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 5px;
          padding: 4px;
          border-radius: var(--r-pill);
          background: rgba(0, 0, 0, .35);
        }
        .control-scroll {
          min-height: 0;
          overflow-y: auto;
          padding-right: 2px;
        }
        .stack { display: grid; gap: 16px; }
        .panel-heading,
        .field-label {
          margin: 0 0 8px;
          color: var(--gold-soft);
          font-size: 11px;
          font-weight: 900;
          letter-spacing: .14em;
          text-transform: uppercase;
        }
        .name-input {
          width: 100%;
          min-height: 48px;
          border-radius: var(--r-md);
          border: 1px solid rgba(248, 236, 210, .18);
          background: rgba(248, 236, 210, .07);
          color: var(--ink-on-dark);
          padding: 0 13px;
          font-size: 17px;
          font-weight: 800;
          outline: none;
        }
        .name-input:focus {
          border-color: rgba(217, 167, 58, .72);
          box-shadow: 0 0 0 2px rgba(217, 167, 58, .18);
        }
        .seg {
          display: inline-flex;
          gap: 4px;
          padding: 3px;
          border-radius: var(--r-pill);
          background: rgba(0, 0, 0, .4);
          border: 1px solid rgba(248, 236, 210, .08);
        }
        .card-options { display: grid; gap: 8px; }
        .big-card {
          position: relative;
          border: 1px solid rgba(248, 236, 210, .12);
          background: rgba(248, 236, 210, .05);
          color: var(--ink-on-dark);
          border-radius: var(--r-md);
          padding: 11px 12px;
          text-align: left;
          cursor: pointer;
          transition: border-color .14s, background .14s, transform .12s;
        }
        .big-card:hover { transform: translateY(-1px); }
        .big-card.is-on {
          border-color: rgba(217, 167, 58, .72);
          background: rgba(217, 167, 58, .14);
          box-shadow: 0 0 0 2px rgba(217, 167, 58, .16);
        }
        .big-card-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
        .big-card b { font-size: 15px; font-family: var(--font-display); }
        .big-card small { display: block; margin-top: 3px; color: var(--muted-on-dark); font-size: 12px; line-height: 1.3; }
        .badge {
          font-size: 10px;
          font-weight: 800;
          letter-spacing: .06em;
          color: var(--gold-soft);
          border: 1px solid rgba(217, 167, 58, .4);
          border-radius: var(--r-pill);
          padding: 2px 8px;
        }
        .card-check { position: absolute; top: 10px; right: 10px; color: var(--gold-soft); }
        .outfit-options { display: grid; gap: 8px; }
        .outfit-row {
          display: grid;
          grid-template-columns: 36px 1fr 18px;
          gap: 10px;
          align-items: center;
          min-height: 56px;
          padding: 8px;
          border-radius: var(--r-md);
          border: 1px solid rgba(248, 236, 210, .12);
          background: rgba(248, 236, 210, .05);
          color: var(--ink-on-dark);
          cursor: pointer;
          text-align: left;
        }
        .outfit-row.is-on {
          border-color: rgba(217, 167, 58, .72);
          background: rgba(217, 167, 58, .13);
        }
        .outfit-swatch { width: 34px; height: 34px; border-radius: 50%; border: 1px solid rgba(255, 255, 255, .34); }
        .outfit-meta b { display: block; font-size: 13px; }
        .outfit-meta small { display: block; margin-top: 2px; color: var(--muted-on-dark); font-size: 11px; line-height: 1.25; }
        .chip-grid { display: flex; flex-wrap: wrap; gap: 7px; }
        .chip {
          min-height: 40px;
          padding: 8px 13px;
          border-radius: var(--r-pill);
          border: 1px solid rgba(248, 236, 210, .14);
          background: rgba(248, 236, 210, .05);
          color: var(--ink-on-dark);
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: border-color .14s, background .14s;
        }
        .chip.is-on {
          border-color: rgba(217, 167, 58, .72);
          background: rgba(217, 167, 58, .16);
          color: var(--card);
        }

        .preview-zone {
          min-height: 0;
          display: grid;
          grid-template-rows: minmax(0, 1fr) auto;
          gap: 12px;
        }
        .casting-card {
          position: relative;
          min-height: 0;
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
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 60vw;
        }
        .nameplate-sub {
          font-size: 10px;
          letter-spacing: .14em;
          text-transform: uppercase;
          color: var(--gold-soft);
        }
        .badge-rail {
          position: absolute;
          top: 12px;
          right: 12px;
          z-index: 4;
        }
        .preview-actions { display: grid; gap: 10px; }
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

        .summary { gap: 14px; }
        .profile-card {
          display: grid;
          grid-template-columns: 92px 1fr;
          gap: 12px;
          align-items: center;
          padding-bottom: 12px;
          border-bottom: 1px solid rgba(248, 236, 210, .12);
        }
        .mini-card {
          width: 88px;
          height: 120px;
          border-radius: var(--r-md);
          overflow: hidden;
          border: 1px solid rgba(217, 167, 58, .24);
        }
        .profile-name { margin: 2px 0 0; font-family: var(--font-display); font-size: 24px; color: var(--card); }
        .profile-line { margin: 5px 0 0; color: var(--muted-on-dark); font-size: 13px; }
        .summary-list { display: grid; gap: 8px; padding-bottom: 12px; border-bottom: 1px solid rgba(248, 236, 210, .12); }
        .summary-row { display: grid; grid-template-columns: 64px 1fr; gap: 8px; align-items: baseline; font-size: 12.5px; }
        .summary-row b { color: var(--gold-soft); font-size: 10px; letter-spacing: .1em; text-transform: uppercase; }
        .summary-row span { color: var(--muted-on-dark); }
        .acc-summary { display: grid; gap: 8px; }
        .acc-empty { margin: 0; color: var(--muted-on-dark); font-size: 12.5px; font-style: italic; }
        .acc-tags { display: flex; flex-wrap: wrap; gap: 6px; }
        .acc-tag {
          font-size: 12px;
          padding: 4px 10px;
          border-radius: var(--r-pill);
          background: rgba(217, 167, 58, .12);
          border: 1px solid rgba(217, 167, 58, .3);
          color: var(--ink-on-dark);
        }
        .reassure {
          margin: auto 0 0;
          display: flex;
          align-items: center;
          gap: 6px;
          color: var(--muted-on-dark);
          font-size: 12px;
          font-style: italic;
        }
        .reassure :global(svg) { color: var(--gold-soft); flex-shrink: 0; }

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

        @media (max-width: 1100px) {
          .creator-layout { grid-template-columns: minmax(280px, 340px) minmax(320px, 1fr); }
          .summary { display: none; }
        }
        @media (max-width: 760px) {
          .creator-page {
            height: auto;
            min-height: 100svh;
            overflow: visible;
          }
          .creator-layout {
            flex: initial;
            min-height: 0;
            grid-template-columns: 1fr;
            grid-template-rows: minmax(380px, 52svh) auto;
          }
          .preview-zone { order: 1; }
          .controls { order: 2; }
          .control-scroll { overflow: visible; }
          .top-action span { display: none; }
          .top-action { width: 42px; padding: 0; }
          .checkpoint-grid { grid-template-columns: 1fr; }
        }
      `}</style>
    </main>
  );
}

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function TabButton({ active, children, onClick }: { active: boolean; children: string; onClick: () => void }) {
  return (
    <button type="button" role="tab" aria-selected={active} className={`tab${active ? " is-on" : ""}`} onClick={onClick}>
      {children}
      <style jsx>{`
        .tab {
          min-height: 36px;
          border: 0;
          border-radius: var(--r-pill);
          background: transparent;
          color: var(--muted-on-dark);
          font-size: 11px;
          font-weight: 900;
          letter-spacing: .08em;
          text-transform: uppercase;
          cursor: pointer;
        }
        .tab.is-on {
          background: linear-gradient(180deg, var(--accent), var(--accent-deep));
          color: var(--card);
          box-shadow: var(--shadow-sm), var(--inset-gold);
        }
      `}</style>
    </button>
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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section>
      <p className="field-label">{label}</p>
      {children}
      <style jsx>{`
        .field-label {
          margin: 0 0 8px;
          color: var(--gold-soft);
          font-size: 11px;
          font-weight: 900;
          letter-spacing: .14em;
          text-transform: uppercase;
        }
      `}</style>
    </section>
  );
}

function SwatchField({
  title,
  options,
  value,
  onChange,
  labelled,
}: {
  title: string;
  options: { id: string; label: string; detail: string; value: string }[];
  value: string;
  onChange: (id: string) => void;
  labelled?: boolean;
}) {
  return (
    <section>
      <p className="field-label">{title}</p>
      <div className="swatch-row">
        {options.map((o) => (
          <button
            key={o.id}
            type="button"
            className={`swatch-btn${value === o.id ? " is-on" : ""}`}
            onClick={() => onChange(o.id)}
            aria-label={`${title}: ${o.label}`}
            aria-pressed={value === o.id}
            title={o.detail}
          >
            <span className="swatch-dot" style={{ background: o.value }} />
            {labelled ? <span className="swatch-text">{o.label}</span> : null}
          </button>
        ))}
      </div>
      <style jsx>{`
        .field-label {
          margin: 0 0 8px;
          color: var(--gold-soft);
          font-size: 11px;
          font-weight: 900;
          letter-spacing: .14em;
          text-transform: uppercase;
        }
        .swatch-row { display: flex; flex-wrap: wrap; gap: 8px; }
        .swatch-btn {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          padding: 5px;
          padding-right: ${labelled ? "12px" : "5px"};
          border-radius: ${labelled ? "var(--r-pill)" : "50%"};
          border: 1px solid rgba(248, 236, 210, .14);
          background: rgba(248, 236, 210, .05);
          cursor: pointer;
        }
        .swatch-btn.is-on {
          border-color: rgba(217, 167, 58, .8);
          box-shadow: 0 0 0 2px rgba(217, 167, 58, .2);
        }
        .swatch-dot {
          width: 30px;
          height: 30px;
          border-radius: 50%;
          border: 1px solid rgba(255, 255, 255, .42);
          box-shadow: inset 0 0 0 2px rgba(0, 0, 0, .18);
        }
        .swatch-text { font-size: 12px; font-weight: 700; color: var(--ink-on-dark); }
      `}</style>
    </section>
  );
}

function SummaryRows({ rows }: { rows: [string, string][] }) {
  return (
    <div className="summary-list">
      {rows.map(([label, value]) => (
        <p className="summary-row" key={label}>
          <b>{label}</b>
          <span>{value}</span>
        </p>
      ))}
    </div>
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
