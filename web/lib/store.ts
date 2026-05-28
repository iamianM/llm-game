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

function initialLiveLlm(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(LLM_KEY) === "1";
}

export const useUiStore = create<UiStore>((set) => ({
  rightRailOpen: false,
  settingsOpen: false,
  reduceMotion: false,
  typewriterSpeed: "normal",
  useLiveLlm: initialLiveLlm(),
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
