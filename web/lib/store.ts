import { create } from "zustand";

type Speed = "slow" | "normal" | "fast" | "instant";

type UiStore = {
  rightRailOpen: boolean;
  settingsOpen: boolean;
  reduceMotion: boolean;
  typewriterSpeed: Speed;
  useLiveLlm: boolean;
  setRail: (open: boolean) => void;
  setSettings: (open: boolean) => void;
  setReduceMotion: (value: boolean) => void;
  setTypewriterSpeed: (value: Speed) => void;
  setUseLiveLlm: (value: boolean) => void;
};

const LLM_KEY = "paradise.settings.useLiveLlm";
export const DEFAULT_USE_LIVE_LLM = process.env.NEXT_PUBLIC_DEFAULT_LIVE_LLM === "1";

// NOTE: the initial value MUST be the same on server and client to avoid
// hydration mismatches; React 18 silently keeps the server HTML when it
// detects the toggle's aria-pressed differs, and the user gets stuck
// looking at Demo even when localStorage has Live picked. Components hydrate
// this value from localStorage via useEffect after mount instead.
export const useUiStore = create<UiStore>((set) => ({
  rightRailOpen: false,
  settingsOpen: false,
  reduceMotion: false,
  typewriterSpeed: "normal",
  useLiveLlm: DEFAULT_USE_LIVE_LLM,
  setRail: (open) => set({ rightRailOpen: open }),
  setSettings: (open) => set({ settingsOpen: open }),
  setReduceMotion: (value) => set({ reduceMotion: value }),
  setTypewriterSpeed: (value) => set({ typewriterSpeed: value }),
  setUseLiveLlm: (value) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LLM_KEY, value ? "1" : "0");
    }
    set({ useLiveLlm: value });
  }
}));
