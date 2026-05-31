import { useUiStore } from "./store";

// The one-shot sound-effect layer. Separate from the looping background score
// (see MusicPlayer): these are short, fire-and-forget cues triggered by game
// events — a click, a stat pop, a ceremony reveal. They share the master Music
// switch (musicOn) so a single mute silences everything, but they keep fixed
// per-cue gains rather than riding the "Music volume" slider, which is meant
// for the bed, not for UI feedback.
export type SfxName =
  | "ui-click"
  | "ui-advance"
  | "choice-open"
  | "modal-open"
  | "modal-close"
  | "new-run"
  | "connection-up"
  | "connection-down"
  | "pulse-up"
  | "pulse-down"
  | "ceremony-reveal"
  | "text-alert";

// Hand-tuned levels: UI ticks sit quietly under dialogue, stat cues and the
// text alert are a touch louder, and the ceremony sting gets the most presence.
const GAINS: Record<SfxName, number> = {
  "ui-click": 0.32,
  "ui-advance": 0.28,
  "choice-open": 0.34,
  "modal-open": 0.36,
  "modal-close": 0.32,
  "new-run": 0.5,
  "connection-up": 0.48,
  "connection-down": 0.46,
  "pulse-up": 0.46,
  "pulse-down": 0.44,
  "ceremony-reveal": 0.6,
  "text-alert": 0.55,
};

const NAMES = Object.keys(GAINS) as SfxName[];

// One preloaded element per cue. We clone it on each play so rapid or
// overlapping triggers (a stat pop landing mid-click) don't cut each other off.
const buffers: Partial<Record<SfxName, HTMLAudioElement>> = {};

const srcFor = (name: SfxName) => `/audio/sfx/${name}.mp3`;

export function preloadSfx() {
  if (typeof Audio === "undefined") return;
  for (const name of NAMES) {
    if (!buffers[name]) {
      const el = new Audio(srcFor(name));
      el.preload = "auto";
      buffers[name] = el;
    }
  }
}

export function playSfx(name: SfxName) {
  if (typeof Audio === "undefined") return;
  // The master Music switch gates SFX too — muting the game mutes all of it.
  if (!useUiStore.getState().musicOn) return;
  let base = buffers[name];
  if (!base) {
    base = new Audio(srcFor(name));
    buffers[name] = base;
  }
  const node = base.cloneNode(true) as HTMLAudioElement;
  node.volume = Math.min(1, Math.max(0, GAINS[name]));
  node.play().catch(() => {});
}
