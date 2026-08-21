"use client";

import { type MutableRefObject, useEffect, useRef } from "react";
import {
  MUSIC_MUTE_KEY,
  MUSIC_OUTPUT_CEILING,
  MUSIC_VOLUME_KEY,
  type MusicScene,
  useUiStore,
} from "../../lib/store";

type FadeTimer = ReturnType<typeof setInterval> | null;

// The mood-to-track map. Each scene owns one looping bed; the play screen
// nudges the scene as the game phase changes (see GameStage) and the title /
// creator / finale routes sit on "title".
const TRACKS: Record<MusicScene, string> = {
  title: "/audio/music/title-theme.mp3",
  day: "/audio/music/resort-day.mp3",
  evening: "/audio/music/resort-evening.mp3",
  tension: "/audio/music/tension.mp3",
};

const CROSSFADE_MS = 1100;
const FADE_STEP_MS = 50;

// Single app-wide background-music engine. Mounted once in the root layout so
// the score keeps playing seamlessly across client navigation (title -> run ->
// finale). Two stacked <audio> elements let one bed fade out while the next
// fades in — a bare `src` swap would click and leave a silent gap. Playback
// state and the current scene live in the UI store.
export function MusicPlayer() {
  const musicOn = useUiStore((s) => s.musicOn);
  const musicVolume = useUiStore((s) => s.musicVolume);
  const musicScene = useUiStore((s) => s.musicScene);
  const setMusicOn = useUiStore((s) => s.setMusicOn);
  const setMusicVolume = useUiStore((s) => s.setMusicVolume);

  const aRef = useRef<HTMLAudioElement | null>(null);
  const bRef = useRef<HTMLAudioElement | null>(null);
  // Which element currently owns the music; the other is the idle fade target.
  const activeRef = useRef<"a" | "b">("a");
  // The track path the active element is (or is becoming) responsible for.
  const currentTrackRef = useRef<string | null>(null);
  const fadeTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Latest target volume, read by the fade loop so a mid-fade volume change
  // (slider drag) lands on the right ceiling.
  const targetVolumeRef = useRef(outputVolume(musicVolume));

  const elFor = (which: "a" | "b") => (which === "a" ? aRef.current : bRef.current);

  // Hydrate the saved preferences after mount (kept out of the store's initial
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

  // Keep the live (non-fading) volume in sync with the slider. While a fade is
  // running, only update the target — the fade loop owns the element volumes.
  useEffect(() => {
    targetVolumeRef.current = outputVolume(musicVolume);
    if (fadeTimerRef.current === null && musicOn) {
      const active = elFor(activeRef.current);
      if (active) active.volume = targetVolumeRef.current;
    }
  }, [musicVolume, musicOn]);

  // The crossfade driver: react to scene changes (and to music being switched
  // back on) by ramping the active element down and the incoming one up.
  useEffect(() => {
    const target = TRACKS[musicScene];

    if (!musicOn) {
      stopFade(fadeTimerRef);
      aRef.current?.pause();
      bRef.current?.pause();
      return;
    }

    // Already sitting on the right track: just make sure it's audible & playing
    // (covers the un-mute path and the autoplay-unblock retry).
    if (currentTrackRef.current === target) {
      const active = elFor(activeRef.current);
      if (active) {
        active.volume = targetVolumeRef.current;
        active.play().catch(() => {});
      }
      return;
    }

    const fromWhich = activeRef.current;
    const toWhich: "a" | "b" = fromWhich === "a" ? "b" : "a";
    const fromEl = currentTrackRef.current ? elFor(fromWhich) : null;
    const toEl = elFor(toWhich);
    if (!toEl) return;

    if (!toEl.src.endsWith(target)) toEl.src = target;
    toEl.currentTime = 0;
    toEl.volume = 0;
    toEl.loop = true;
    const started = toEl.play();
    activeRef.current = toWhich;
    currentTrackRef.current = target;

    const runFade = () => crossfade(fadeTimerRef, fromEl, toEl, () => targetVolumeRef.current);
    // If autoplay is blocked the promise rejects; the gesture fallback below
    // retries. Only start the volume ramp once playback is actually going.
    if (started && typeof started.then === "function") {
      started.then(runFade).catch(() => {});
    } else {
      runFade();
    }
  }, [musicScene, musicOn]);

  // Browsers block audio until a user gesture. Arm a one-shot retry that kicks
  // the active element on the visitor's first interaction.
  useEffect(() => {
    const retry = () => {
      if (!useUiStore.getState().musicOn) return;
      const active = elFor(activeRef.current);
      if (active && active.paused) {
        active.volume = targetVolumeRef.current;
        active.play().catch(() => {});
      }
    };
    window.addEventListener("pointerdown", retry, { once: true });
    window.addEventListener("keydown", retry, { once: true });
    return () => {
      window.removeEventListener("pointerdown", retry);
      window.removeEventListener("keydown", retry);
    };
  }, []);

  // Pause the score while the tab/app is backgrounded (e.g. the player
  // minimizes the browser) and resume it on return. Without this the loop keeps
  // playing under a hidden window with no way to stop it.
  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden) {
        aRef.current?.pause();
        bRef.current?.pause();
        return;
      }
      if (!useUiStore.getState().musicOn) return;
      const active = elFor(activeRef.current);
      if (active && active.paused) {
        active.volume = targetVolumeRef.current;
        active.play().catch(() => {});
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  // Clear any running fade on unmount.
  useEffect(() => () => stopFade(fadeTimerRef), []);

  return (
    <>
      <audio ref={aRef} preload="auto" />
      <audio ref={bRef} preload="auto" />
    </>
  );
}

function stopFade(timerRef: MutableRefObject<FadeTimer>) {
  if (timerRef.current !== null) {
    clearInterval(timerRef.current);
    timerRef.current = null;
  }
}

// Linearly ramp `toEl` up to the live target volume and `fromEl` down to 0 over
// CROSSFADE_MS, then pause the outgoing element. Reads the target each tick so
// a slider drag mid-fade is honored.
function crossfade(
  timerRef: MutableRefObject<FadeTimer>,
  fromEl: HTMLAudioElement | null,
  toEl: HTMLAudioElement,
  getTarget: () => number,
) {
  stopFade(timerRef);
  const steps = Math.max(1, Math.round(CROSSFADE_MS / FADE_STEP_MS));
  let step = 0;
  timerRef.current = setInterval(() => {
    step += 1;
    const progress = Math.min(1, step / steps);
    const target = getTarget();
    toEl.volume = clamp01(target * progress);
    if (fromEl) fromEl.volume = clamp01(target * (1 - progress));
    if (progress >= 1) {
      stopFade(timerRef);
      if (fromEl) {
        fromEl.pause();
        fromEl.volume = target;
      }
    }
  }, FADE_STEP_MS);
}

function clamp01(value: number) {
  return Math.min(1, Math.max(0, value));
}

function outputVolume(preference: number) {
  return clamp01(preference) * MUSIC_OUTPUT_CEILING;
}
