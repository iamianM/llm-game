import { create } from "zustand";

type Speed = "slow" | "normal" | "fast" | "instant";

type UiStore = {
  rightRailOpen: boolean;
  settingsOpen: boolean;
  wardrobeOpen: boolean;
  reduceMotion: boolean;
  typewriterSpeed: Speed;
  useLiveLlm: boolean;
  musicOn: boolean;
  musicVolume: number;
  setRail: (open: boolean) => void;
  setSettings: (open: boolean) => void;
  setWardrobe: (open: boolean) => void;
  setReduceMotion: (value: boolean) => void;
  setTypewriterSpeed: (value: Speed) => void;
  setUseLiveLlm: (value: boolean) => void;
  setMusicOn: (value: boolean) => void;
  setMusicVolume: (value: number) => void;
};

const LLM_KEY = "paradise.settings.useLiveLlm";
export const MUSIC_MUTE_KEY = "ph-title-muted";
export const MUSIC_VOLUME_KEY = "ph-title-volume";
export const DEFAULT_MUSIC_VOLUME = 0.32;
export const DEFAULT_USE_LIVE_LLM = process.env.NEXT_PUBLIC_DEFAULT_LIVE_LLM === "1";

// NOTE: the initial value MUST be the same on server and client to avoid
// hydration mismatches; React 18 silently keeps the server HTML when it
// detects the toggle's aria-pressed differs, and the user gets stuck
// looking at Demo even when localStorage has Live picked. Components hydrate
// this value from localStorage via useEffect after mount instead.
export const useUiStore = create<UiStore>((set) => ({
  rightRailOpen: false,
  settingsOpen: false,
  wardrobeOpen: false,
  reduceMotion: false,
  typewriterSpeed: "normal",
  useLiveLlm: DEFAULT_USE_LIVE_LLM,
  musicOn: true,
  musicVolume: DEFAULT_MUSIC_VOLUME,
  setRail: (open) => set({ rightRailOpen: open }),
  setSettings: (open) => set({ settingsOpen: open }),
  setWardrobe: (open) => set({ wardrobeOpen: open }),
  setReduceMotion: (value) => set({ reduceMotion: value }),
  setTypewriterSpeed: (value) => set({ typewriterSpeed: value }),
  setUseLiveLlm: (value) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LLM_KEY, value ? "1" : "0");
    }
    set({ useLiveLlm: value });
  },
  setMusicOn: (value) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(MUSIC_MUTE_KEY, value ? "0" : "1");
    }
    set({ musicOn: value });
  },
  setMusicVolume: (value) => {
    const clamped = Math.min(1, Math.max(0, value));
    if (typeof window !== "undefined") {
      window.localStorage.setItem(MUSIC_VOLUME_KEY, String(clamped));
    }
    set({ musicVolume: clamped });
  }
}));
