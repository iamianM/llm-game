import { create } from "zustand";

type Speed = "slow" | "normal" | "fast" | "instant";

type UiStore = {
  rightRailOpen: boolean;
  settingsOpen: boolean;
  reduceMotion: boolean;
  typewriterSpeed: Speed;
  setRail: (open: boolean) => void;
  setSettings: (open: boolean) => void;
  setReduceMotion: (value: boolean) => void;
  setTypewriterSpeed: (value: Speed) => void;
};

export const useUiStore = create<UiStore>((set) => ({
  rightRailOpen: false,
  settingsOpen: false,
  reduceMotion: false,
  typewriterSpeed: "normal",
  setRail: (open) => set({ rightRailOpen: open }),
  setSettings: (open) => set({ settingsOpen: open }),
  setReduceMotion: (value) => set({ reduceMotion: value }),
  setTypewriterSpeed: (value) => set({ typewriterSpeed: value })
}));
