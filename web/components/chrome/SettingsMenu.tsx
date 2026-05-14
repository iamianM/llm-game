"use client";

import { useUiStore } from "../../lib/store";
import { Button } from "../ui/Button";

export function SettingsMenu() {
  const open = useUiStore((s) => s.settingsOpen);
  const setOpen = useUiStore((s) => s.setSettings);
  const speed = useUiStore((s) => s.typewriterSpeed);
  const setSpeed = useUiStore((s) => s.setTypewriterSpeed);
  const reduce = useUiStore((s) => s.reduceMotion);
  const setReduce = useUiStore((s) => s.setReduceMotion);
  if (!open) return null;
  return (
    <div className="relative z-50">
      <div className="fixed inset-0 bg-black/60" aria-hidden="true" />
      <div role="dialog" aria-modal="true" aria-labelledby="settings-title" className="fixed inset-0 grid place-items-center p-6">
        <section className="w-full max-w-md rounded-[var(--r-lg)] bg-card p-6 text-ink">
          <h2 id="settings-title" className="font-display text-3xl text-accent">Settings</h2>
          <label className="mt-5 block text-sm font-semibold">Typewriter speed</label>
          <select aria-label="Typewriter speed" value={speed} onChange={(event) => setSpeed(event.target.value as typeof speed)} className="mt-2 w-full rounded border border-line bg-white p-2">
            <option value="slow">Slow</option>
            <option value="normal">Normal</option>
            <option value="fast">Fast</option>
            <option value="instant">Instant</option>
          </select>
          <label className="mt-4 flex items-center gap-2 text-sm">
            <input aria-label="Reduce motion" type="checkbox" checked={reduce} onChange={(event) => setReduce(event.target.checked)} />
            Reduce motion
          </label>
          <p className="mt-4 text-sm text-[var(--muted)]">Audio controls arrive in a later phase.</p>
          <Button className="mt-6" onClick={() => setOpen(false)}>Close</Button>
        </section>
      </div>
    </div>
  );
}
