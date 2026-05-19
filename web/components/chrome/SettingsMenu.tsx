"use client";

import { X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useUiStore } from "../../lib/store";

export function SettingsMenu() {
  const router = useRouter();
  const open = useUiStore((s) => s.settingsOpen);
  const setOpen = useUiStore((s) => s.setSettings);
  const speed = useUiStore((s) => s.typewriterSpeed);
  const setSpeed = useUiStore((s) => s.setTypewriterSpeed);
  const reduce = useUiStore((s) => s.reduceMotion);
  const setReduce = useUiStore((s) => s.setReduceMotion);
  if (!open) return null;
  return (
    <div className="settings-root">
      <button className="settings-backdrop" aria-label="Close settings" onClick={() => setOpen(false)} />
      <div role="dialog" aria-modal="true" aria-labelledby="settings-title" className="settings-frame">
        <section className="settings-card">
          <header className="settings-head">
            <p className="settings-eyebrow">Configuration</p>
            <h2 id="settings-title">Settings</h2>
            <button onClick={() => setOpen(false)} className="settings-close" aria-label="Close"><X size={18} /></button>
          </header>
          <div className="settings-body">
            <div className="setting-row">
              <label htmlFor="ts-speed">Typewriter speed</label>
              <select
                id="ts-speed"
                value={speed}
                onChange={(event) => setSpeed(event.target.value as typeof speed)}
                className="setting-select"
              >
                <option value="slow">Slow · 18 cps</option>
                <option value="normal">Normal · 30 cps</option>
                <option value="fast">Fast · 55 cps</option>
                <option value="instant">Instant</option>
              </select>
            </div>

            <div className="setting-row">
              <span className="setting-label">Reduce motion</span>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={reduce}
                  onChange={(event) => setReduce(event.target.checked)}
                  aria-label="Reduce motion"
                />
                <span className="track"><span className="dot" /></span>
              </label>
            </div>

            <p className="setting-hint">Audio controls arrive in a later phase.</p>

            <button
              type="button"
              className="main-menu-btn"
              onClick={() => {
                setOpen(false);
                router.push("/");
              }}
            >
              Return to Main Menu
            </button>
          </div>
        </section>
      </div>

      <style jsx>{`
        .settings-root { position: relative; z-index: 50; }
        .settings-backdrop {
          position: fixed; inset: 0;
          background: rgba(4,3,2,.7);
          backdrop-filter: blur(8px);
          border: 0;
          cursor: pointer;
        }
        .settings-frame {
          position: fixed; inset: 0;
          display: grid;
          place-items: center;
          padding: 24px;
        }
        .settings-card {
          width: 100%;
          max-width: 460px;
          border-radius: var(--r-xl);
          background: linear-gradient(180deg, #1a130d 0%, #100a07 100%);
          border: 1px solid rgba(217,167,58,.32);
          box-shadow: var(--shadow-stage), var(--inset-gold);
          color: var(--ink-on-dark);
          overflow: hidden;
          animation: drift-up .3s cubic-bezier(.22,.61,.36,1) both;
        }
        .settings-head {
          position: relative;
          padding: 18px 22px 14px;
          background: radial-gradient(80% 60% at 30% 0%, rgba(217,167,58,.12), transparent 60%);
          border-bottom: 1px solid rgba(217,167,58,.18);
        }
        .settings-eyebrow {
          margin: 0;
          font-size: 10px;
          letter-spacing: .16em;
          text-transform: uppercase;
          font-weight: 700;
          color: var(--gold-soft);
        }
        .settings-head h2 {
          margin: 4px 0 0;
          font-family: var(--font-display);
          font-size: 28px;
          color: var(--card);
        }
        .settings-close {
          position: absolute;
          right: 14px; top: 18px;
          display: grid; place-items: center;
          width: 30px; height: 30px;
          border-radius: var(--r-md);
          border: 1px solid rgba(217,167,58,.3);
          background: rgba(8,6,4,.5);
          color: var(--gold-soft);
          cursor: pointer;
        }
        .settings-close:hover { background: rgba(217,167,58,.18); color: var(--card); }

        .settings-body {
          padding: 20px 22px 22px;
          display: grid;
          gap: 18px;
        }
        .setting-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }
        .setting-row label, .setting-label {
          font-size: 14px;
          color: var(--ink-on-dark);
          letter-spacing: .02em;
        }
        .setting-select {
          padding: 8px 12px;
          border-radius: var(--r-md);
          background: rgba(8,6,4,.6);
          border: 1px solid rgba(217,167,58,.32);
          color: var(--ink-on-dark);
          font-family: var(--font-body);
          font-size: 13px;
          cursor: pointer;
        }
        .setting-hint {
          margin: 6px 0 0;
          font-size: 12px;
          color: var(--muted-on-dark);
          opacity: .8;
          font-style: italic;
        }
        .switch { position: relative; display: inline-block; width: 44px; height: 24px; }
        .switch input {
          position: absolute; inset: 0;
          width: 100%; height: 100%;
          margin: 0;
          opacity: 0;
          cursor: pointer;
          z-index: 2;
        }
        .switch .track {
          display: block;
          width: 44px; height: 24px;
          border-radius: var(--r-pill);
          background: rgba(8,6,4,.6);
          border: 1px solid rgba(217,167,58,.3);
          transition: background .2s;
          position: relative;
        }
        .switch .dot {
          position: absolute;
          left: 2px; top: 2px;
          width: 18px; height: 18px;
          border-radius: 50%;
          background: var(--gold-soft);
          transition: left .25s cubic-bezier(.22,.61,.36,1);
          box-shadow: 0 0 12px rgba(217,167,58,.45);
        }
        .switch input:checked + .track { background: rgba(217,167,58,.3); }
        .switch input:checked + .track .dot { left: 22px; background: var(--gold); }

        .main-menu-btn {
          margin-top: 4px;
          padding: 10px 16px;
          border-radius: var(--r-md);
          background: rgba(8,6,4,.55);
          border: 1px solid rgba(217,167,58,.35);
          color: var(--ink-on-dark);
          font-family: var(--font-display);
          font-size: 14px;
          font-style: italic;
          letter-spacing: .02em;
          cursor: pointer;
          transition: background .15s, border-color .15s, color .15s;
        }
        .main-menu-btn:hover {
          background: rgba(217,167,58,.18);
          border-color: rgba(217,167,58,.6);
          color: var(--card);
        }
      `}</style>
    </div>
  );
}
