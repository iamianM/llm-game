"use client";

import { useEffect, useRef } from "react";
import { type MusicScene, useUiStore } from "../../lib/store";

// A low bed of resort room-tone that sits *under* the music, not instead of it.
// Daytime scenes (and the title) get the bright day loop; evenings and tense
// beats get the night loop. Volume stays well below the score so it reads as
// atmosphere, never as a second track competing with it.
const AMBIENCE: Record<MusicScene, string> = {
  title: "/audio/ambience/resort-day.mp3",
  day: "/audio/ambience/resort-day.mp3",
  evening: "/audio/ambience/resort-night.mp3",
  tension: "/audio/ambience/resort-night.mp3",
};

const AMBIENCE_VOLUME = 0.16;
const CROSSFADE_MS = 1400;
const FADE_STEP_MS = 60;

// Mounted once in the root layout alongside MusicPlayer. Two stacked <audio>
// elements crossfade so the day/night swap doesn't click. Shares the master
// Music switch (musicOn) but ignores the music-volume slider — the bed has its
// own fixed, deliberately quiet level.
export function AmbiencePlayer() {
  const musicOn = useUiStore((s) => s.musicOn);
  const musicScene = useUiStore((s) => s.musicScene);

  const aRef = useRef<HTMLAudioElement | null>(null);
  const bRef = useRef<HTMLAudioElement | null>(null);
  const activeRef = useRef<"a" | "b">("a");
  const currentTrackRef = useRef<string | null>(null);
  const fadeTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const elFor = (which: "a" | "b") => (which === "a" ? aRef.current : bRef.current);

  useEffect(() => {
    const target = AMBIENCE[musicScene];

    if (!musicOn) {
      stopFade(fadeTimerRef);
      aRef.current?.pause();
      bRef.current?.pause();
      return;
    }

    if (currentTrackRef.current === target) {
      const active = elFor(activeRef.current);
      if (active) {
        active.volume = AMBIENCE_VOLUME;
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

    const runFade = () => crossfade(fadeTimerRef, fromEl, toEl);
    if (started && typeof started.then === "function") {
      started.then(runFade).catch(() => {});
    } else {
      runFade();
    }
  }, [musicScene, musicOn]);

  // Autoplay is gated behind a gesture; kick the active loop on first input.
  useEffect(() => {
    const retry = () => {
      if (!useUiStore.getState().musicOn) return;
      const active = elFor(activeRef.current);
      if (active && active.paused) {
        active.volume = AMBIENCE_VOLUME;
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

  // Pause the room-tone bed while the tab/app is backgrounded and resume it on
  // return, matching the music engine so nothing keeps playing under a hidden
  // window.
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
        active.volume = AMBIENCE_VOLUME;
        active.play().catch(() => {});
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  useEffect(() => () => stopFade(fadeTimerRef), []);

  return (
    <>
      <audio ref={aRef} preload="auto" />
      <audio ref={bRef} preload="auto" />
    </>
  );
}

function stopFade(timerRef: { current: ReturnType<typeof setInterval> | null }) {
  if (timerRef.current !== null) {
    clearInterval(timerRef.current);
    timerRef.current = null;
  }
}

function crossfade(
  timerRef: { current: ReturnType<typeof setInterval> | null },
  fromEl: HTMLAudioElement | null,
  toEl: HTMLAudioElement,
) {
  stopFade(timerRef);
  const steps = Math.max(1, Math.round(CROSSFADE_MS / FADE_STEP_MS));
  let step = 0;
  timerRef.current = setInterval(() => {
    step += 1;
    const progress = Math.min(1, step / steps);
    toEl.volume = clamp01(AMBIENCE_VOLUME * progress);
    if (fromEl) fromEl.volume = clamp01(AMBIENCE_VOLUME * (1 - progress));
    if (progress >= 1) {
      stopFade(timerRef);
      if (fromEl) {
        fromEl.pause();
        fromEl.volume = AMBIENCE_VOLUME;
      }
    }
  }, FADE_STEP_MS);
}

function clamp01(value: number) {
  return Math.min(1, Math.max(0, value));
}
