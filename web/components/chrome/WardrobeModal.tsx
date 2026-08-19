"use client";

import { Check, Shirt, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useUiStore } from "../../lib/store";
import {
  ACCESSORIES,
  OUTFITS,
  VIBES,
  DEFAULT_LOOK,
  findArchetype,
  findOutfit,
  findVibe,
  saveLook,
  type ArchetypeId,
  type HeartbreakerLook,
} from "../../lib/look";
import type { Gender } from "../../lib/types";
import { LookStage } from "../look/LookStage";
import { AccessoryBadges } from "./AccessoryBadges";

type Identity = { name: string; gender: Gender; archetype: ArchetypeId };

type Props = {
  sessionId: string;
  /** Current persisted look for this session (may be null for legacy runs). */
  currentLook: HeartbreakerLook | null;
  /** Fixed character identity from the engine — keeps the standee on-model. */
  identity: Identity;
  /** Called with the new look after the player saves, so the scene restyles live. */
  onApply: (look: HeartbreakerLook) => void;
};

/** Merge the editable cosmetic draft over the locked engine identity. */
function withIdentity(look: HeartbreakerLook, identity: Identity): HeartbreakerLook {
  return { ...look, name: identity.name, gender: identity.gender, archetype: identity.archetype };
}

/**
 * Sunset Bay wardrobe. The creator promises "you can change your look any time at
 * the resort" — this fulfils it. Identity (name / gender / opening archetype) is
 * fixed by the engine, so the modal only edits the cosmetic levers that visibly
 * restyle the in-scene player: outfit palette, accessories, and energy. Saving
 * persists the look recipe to localStorage (Vercel-safe, no runtime image gen)
 * and restyles the live scene immediately.
 */
export function WardrobeModal({ sessionId, currentLook, identity, onApply }: Props) {
  const open = useUiStore((s) => s.wardrobeOpen);
  const setOpen = useUiStore((s) => s.setWardrobe);
  const [draft, setDraft] = useState<HeartbreakerLook>(() =>
    withIdentity(currentLook ?? DEFAULT_LOOK, identity)
  );

  // Re-seed the draft from the latest saved look every time the modal opens so
  // it never shows a stale edit from a cancelled session.
  useEffect(() => {
    if (open) setDraft(withIdentity(currentLook ?? DEFAULT_LOOK, identity));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Escape closes without saving.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  if (!open) return null;

  const toggleAccessory = (id: string) =>
    setDraft((cur) => ({
      ...cur,
      accessories: cur.accessories.includes(id)
        ? cur.accessories.filter((a) => a !== id)
        : [...cur.accessories, id].slice(0, 8),
    }));

  const save = () => {
    const next = withIdentity(draft, identity);
    saveLook(sessionId, next);
    onApply(next);
    setOpen(false);
  };

  const outfit = findOutfit(draft.outfit);
  const archetype = findArchetype(draft.archetype);

  return (
    <div className="wd-root">
      <button className="wd-backdrop" aria-label="Close wardrobe" onClick={() => setOpen(false)} />
      <div role="dialog" aria-modal="true" aria-labelledby="wardrobe-title" className="wd-frame">
        <section className="wd-card">
          <header className="wd-head">
            <p className="wd-eyebrow"><Shirt size={12} /> Sunset Bay Wardrobe</p>
            <h2 id="wardrobe-title">Restyle {identity.name || "your look"}</h2>
            <button onClick={() => setOpen(false)} className="wd-close" aria-label="Close"><X size={18} /></button>
          </header>

          <div className="wd-body">
            {/* Preview */}
            <div className="wd-preview">
              <div className="wd-stage">
                <LookStage look={draft} />
                <div className="wd-nameplate">
                  <span className="wd-name">{identity.name || "Your Heartbreaker"}</span>
                  <span className="wd-sub">{archetype.label} · {findVibe(draft.vibe).label}</span>
                </div>
                <div className="wd-badge-rail">
                  <AccessoryBadges ids={draft.accessories} />
                </div>
              </div>
              <p className="wd-now">{outfit.label} — {outfit.category.toLowerCase()} styling</p>
            </div>

            {/* Controls */}
            <div className="wd-controls">
              <section>
                <p className="wd-label">Outfit</p>
                <div className="wd-outfits">
                  {OUTFITS.map((o) => (
                    <button
                      key={o.id}
                      type="button"
                      className={`wd-outfit${draft.outfit === o.id ? " is-on" : ""}`}
                      onClick={() => setDraft((cur) => ({ ...cur, outfit: o.id }))}
                    >
                      <span className="wd-swatch" style={{ background: `linear-gradient(135deg, ${o.primary}, ${o.secondary})` }} />
                      <span className="wd-outfit-meta">
                        <b>{o.label}</b>
                        <small>{o.detail}</small>
                      </span>
                      {draft.outfit === o.id ? <Check size={15} /> : null}
                    </button>
                  ))}
                </div>
              </section>

              <section>
                <p className="wd-label">Energy</p>
                <div className="wd-swatch-row">
                  {VIBES.map((v) => (
                    <button
                      key={v.id}
                      type="button"
                      className={`wd-energy${draft.vibe === v.id ? " is-on" : ""}`}
                      onClick={() => setDraft((cur) => ({ ...cur, vibe: v.id }))}
                      aria-pressed={draft.vibe === v.id}
                      title={v.detail}
                    >
                      <span className="wd-dot" style={{ background: v.value }} />
                      <span>{v.label}</span>
                    </button>
                  ))}
                </div>
              </section>

              <section>
                <p className="wd-label">Accessories ({draft.accessories.length})</p>
                <div className="wd-chips">
                  {ACCESSORIES.map((a) => {
                    const on = draft.accessories.includes(a.id);
                    return (
                      <button
                        key={a.id}
                        type="button"
                        aria-pressed={on}
                        className={`wd-chip${on ? " is-on" : ""}`}
                        onClick={() => toggleAccessory(a.id)}
                      >
                        {a.label}
                      </button>
                    );
                  })}
                </div>
              </section>
            </div>
          </div>

          <footer className="wd-foot">
            <button type="button" className="wd-cancel" onClick={() => setOpen(false)}>Cancel</button>
            <button type="button" className="wd-save" onClick={save}>
              <Check size={16} /> Wear this look
            </button>
          </footer>
        </section>
      </div>

      <style jsx>{`
        .wd-root { position: relative; z-index: 55; }
        .wd-backdrop {
          position: fixed; inset: 0;
          background: rgba(4, 3, 2, .72);
          backdrop-filter: blur(8px);
          border: 0;
          cursor: pointer;
        }
        .wd-frame {
          position: fixed; inset: 0;
          display: grid;
          place-items: center;
          padding: 18px;
        }
        .wd-card {
          width: 100%;
          max-width: 820px;
          max-height: min(92svh, 760px);
          display: grid;
          grid-template-rows: auto minmax(0, 1fr) auto;
          border-radius: var(--r-xl);
          background: linear-gradient(180deg, #1a130d 0%, #100a07 100%);
          border: 1px solid rgba(217, 167, 58, .32);
          box-shadow: var(--shadow-stage), var(--inset-gold);
          color: var(--ink-on-dark);
          overflow: hidden;
          animation: drift-up .3s cubic-bezier(.22, .61, .36, 1) both;
        }
        .wd-head {
          position: relative;
          padding: 16px 22px 13px;
          background: radial-gradient(80% 60% at 30% 0%, rgba(217, 167, 58, .12), transparent 60%);
          border-bottom: 1px solid rgba(217, 167, 58, .18);
        }
        .wd-eyebrow {
          margin: 0;
          display: inline-flex;
          align-items: center;
          gap: 5px;
          font-size: 10px;
          letter-spacing: .16em;
          text-transform: uppercase;
          font-weight: 800;
          color: var(--gold-soft);
        }
        .wd-head h2 {
          margin: 4px 0 0;
          font-family: var(--font-display);
          font-style: italic;
          font-size: 26px;
          color: var(--card);
        }
        .wd-close {
          position: absolute;
          right: 14px; top: 16px;
          display: grid; place-items: center;
          width: 30px; height: 30px;
          border-radius: var(--r-md);
          border: 1px solid rgba(217, 167, 58, .3);
          background: rgba(8, 6, 4, .5);
          color: var(--gold-soft);
          cursor: pointer;
        }
        .wd-close:hover { background: rgba(217, 167, 58, .18); color: var(--card); }

        .wd-body {
          min-height: 0;
          display: grid;
          grid-template-columns: minmax(220px, 300px) minmax(0, 1fr);
          gap: 16px;
          padding: 16px 22px;
          overflow: hidden;
        }
        .wd-preview {
          display: grid;
          grid-template-rows: minmax(0, 1fr) auto;
          gap: 8px;
          min-height: 0;
        }
        .wd-stage {
          position: relative;
          min-height: 0;
          border-radius: var(--r-lg);
          overflow: hidden;
          border: 1px solid rgba(217, 167, 58, .26);
          box-shadow: var(--inset-gold);
        }
        .wd-nameplate {
          position: absolute;
          left: 50%;
          bottom: 12px;
          transform: translateX(-50%);
          z-index: 4;
          display: grid;
          justify-items: center;
          gap: 2px;
          padding: 6px 16px;
          border-radius: var(--r-pill);
          background: rgba(8, 6, 4, .68);
          border: 1px solid rgba(217, 167, 58, .35);
          backdrop-filter: blur(6px);
          text-align: center;
          max-width: 86%;
        }
        .wd-name {
          font-family: var(--font-display);
          font-size: 20px;
          line-height: 1;
          color: var(--card);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 200px;
        }
        .wd-sub {
          font-size: 9px;
          letter-spacing: .14em;
          text-transform: uppercase;
          color: var(--gold-soft);
        }
        .wd-badge-rail { position: absolute; top: 10px; right: 10px; z-index: 4; }
        .wd-now {
          margin: 0;
          text-align: center;
          font-size: 12px;
          color: var(--muted-on-dark);
          font-style: italic;
        }

        .wd-controls {
          min-height: 0;
          overflow-y: auto;
          padding-right: 4px;
          display: grid;
          gap: 16px;
          align-content: start;
        }
        .wd-label {
          margin: 0 0 8px;
          color: var(--gold-soft);
          font-size: 11px;
          font-weight: 900;
          letter-spacing: .14em;
          text-transform: uppercase;
        }
        .wd-outfits { display: grid; gap: 7px; }
        .wd-outfit {
          display: grid;
          grid-template-columns: 32px 1fr 16px;
          gap: 10px;
          align-items: center;
          min-height: 52px;
          padding: 7px 9px;
          border-radius: var(--r-md);
          border: 1px solid rgba(248, 236, 210, .12);
          background: rgba(248, 236, 210, .05);
          color: var(--ink-on-dark);
          cursor: pointer;
          text-align: left;
          transition: border-color .14s, background .14s;
        }
        .wd-outfit:hover { border-color: rgba(217, 167, 58, .4); }
        .wd-outfit.is-on {
          border-color: rgba(217, 167, 58, .72);
          background: rgba(217, 167, 58, .13);
        }
        .wd-swatch { width: 30px; height: 30px; border-radius: 50%; border: 1px solid rgba(255, 255, 255, .34); }
        .wd-outfit-meta b { display: block; font-size: 13px; }
        .wd-outfit-meta small { display: block; margin-top: 2px; color: var(--muted-on-dark); font-size: 11px; line-height: 1.25; }
        .wd-outfit :global(svg) { color: var(--gold-soft); }

        .wd-swatch-row { display: flex; flex-wrap: wrap; gap: 7px; }
        .wd-energy {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          padding: 6px 12px 6px 6px;
          border-radius: var(--r-pill);
          border: 1px solid rgba(248, 236, 210, .14);
          background: rgba(248, 236, 210, .05);
          color: var(--ink-on-dark);
          font-size: 12px;
          font-weight: 700;
          cursor: pointer;
        }
        .wd-energy.is-on {
          border-color: rgba(217, 167, 58, .8);
          box-shadow: 0 0 0 2px rgba(217, 167, 58, .18);
        }
        .wd-dot {
          width: 22px;
          height: 22px;
          border-radius: 50%;
          border: 1px solid rgba(255, 255, 255, .42);
          box-shadow: inset 0 0 0 2px rgba(0, 0, 0, .18);
        }

        .wd-chips { display: flex; flex-wrap: wrap; gap: 7px; }
        .wd-chip {
          min-height: 38px;
          padding: 7px 13px;
          border-radius: var(--r-pill);
          border: 1px solid rgba(248, 236, 210, .14);
          background: rgba(248, 236, 210, .05);
          color: var(--ink-on-dark);
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: border-color .14s, background .14s;
        }
        .wd-chip.is-on {
          border-color: rgba(217, 167, 58, .72);
          background: rgba(217, 167, 58, .16);
          color: var(--card);
        }

        .wd-foot {
          display: flex;
          align-items: center;
          justify-content: flex-end;
          gap: 10px;
          padding: 13px 22px;
          border-top: 1px solid rgba(217, 167, 58, .18);
          background: rgba(8, 6, 4, .4);
        }
        .wd-cancel {
          min-height: 44px;
          padding: 10px 18px;
          border-radius: var(--r-pill);
          border: 1px solid rgba(248, 236, 210, .16);
          background: rgba(248, 236, 210, .06);
          color: var(--ink-on-dark);
          font-size: 13px;
          font-weight: 700;
          letter-spacing: .04em;
          cursor: pointer;
        }
        .wd-cancel:hover { background: rgba(248, 236, 210, .12); }
        .wd-save {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          min-height: 44px;
          padding: 11px 22px;
          border-radius: var(--r-pill);
          border: 1px solid rgba(217, 167, 58, .55);
          background: linear-gradient(180deg, var(--accent), var(--accent-deep));
          color: var(--card);
          font-family: var(--font-display);
          font-style: italic;
          font-size: 16px;
          cursor: pointer;
          box-shadow: var(--shadow-md), var(--inset-gold);
          transition: transform .16s;
        }
        .wd-save:hover { transform: translateY(-1px); }

        @media (max-width: 640px) {
          .wd-card { max-height: 94svh; }
          .wd-body {
            grid-template-columns: 1fr;
            overflow-y: auto;
            gap: 14px;
          }
          .wd-preview { grid-template-rows: auto auto; }
          .wd-stage { height: 300px; }
          .wd-controls { overflow: visible; }
        }
      `}</style>
    </div>
  );
}
