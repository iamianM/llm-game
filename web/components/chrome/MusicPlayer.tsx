"use client";

import { useEffect, useRef } from "react";
import {
  MUSIC_MUTE_KEY,
  MUSIC_VOLUME_KEY,
  useUiStore,
} from "../../lib/store";

// Single app-wide background-music element. Mounted once in the root layout so
// the title theme keeps playing seamlessly across client navigation (title ->
// run). Playback state lives in the UI store and is mirrored by the title
// screen controls and the in-game settings menu.
export function MusicPlayer() {
  const musicOn = useUiStore((s) => s.musicOn);
  const musicVolume = useUiStore((s) => s.musicVolume);
  const setMusicOn = useUiStore((s) => s.setMusicOn);
  const setMusicVolume = useUiStore((s) => s.setMusicVolume);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Hydrate the saved preference after mount (kept out of the store's initial
  // state to avoid a server/client hydration mismatch).
  useEffect(() => {
    if (window.localStorage.getItem(MUSIC_MUTE_KEY) === "1") {
      setMusicOn(false);
    }
    const stored = window.localStorage.getItem(MUSIC_VOLUME_KEY);
    if (stored !== null) {
      const parsed = Number(stored);
      if (Number.isFinite(parsed)) {
        setMusicVolume(parsed);
      }
    }
  }, [setMusicOn, setMusicVolume]);

  useEffect(() => {
    const audio = audioRef.current;
    if (audio) audio.volume = musicVolume;
  }, [musicVolume]);

  // Browsers block audio until a user gesture, so attempt playback immediately
  // and also arm a one-shot fallback on the visitor's first interaction.
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.volume = musicVolume;
    if (!musicOn) {
      audio.pause();
      return;
    }
    const tryPlay = () => {
      audio.play().catch(() => {});
    };
    tryPlay();
    window.addEventListener("pointerdown", tryPlay, { once: true });
    window.addEventListener("keydown", tryPlay, { once: true });
    return () => {
      window.removeEventListener("pointerdown", tryPlay);
      window.removeEventListener("keydown", tryPlay);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [musicOn]);

  return <audio ref={audioRef} src="/audio/title-theme.mp3" loop preload="auto" />;
}
