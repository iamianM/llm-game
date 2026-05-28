"use client";

import { useEffect, useState } from "react";
import { useUiStore } from "../store";

const CPS_BY_SPEED: Record<string, number> = {
  slow: 26,
  normal: 60,
  fast: 110,
  instant: 0, // 0 means render immediately
};

/**
 * Hook that progressively reveals `text` one character at a time. Returns
 * { rendered, complete }. Tapping/clicking handlers can call
 * `revealAll` to skip the animation; on second click the parent advances.
 *
 * Speed is driven by useUiStore.typewriterSpeed; respects prefers-reduced-motion
 * via useUiStore.reduceMotion (renders instantly).
 */
export function useTypewriter(text: string): { rendered: string; complete: boolean; revealAll: () => void } {
  const speed = useUiStore((s) => s.typewriterSpeed);
  const reduce = useUiStore((s) => s.reduceMotion);
  const cps = CPS_BY_SPEED[speed] ?? CPS_BY_SPEED.normal;
  const instant = cps === 0 || reduce;

  const [visible, setVisible] = useState(() => (instant ? text.length : 0));

  useEffect(() => {
    setVisible(instant ? text.length : 0);
  }, [text, instant]);

  useEffect(() => {
    if (instant || visible >= text.length) return;
    const ms = Math.max(8, Math.round(1000 / cps));
    const id = window.setTimeout(() => setVisible((v) => Math.min(text.length, v + 1)), ms);
    return () => window.clearTimeout(id);
  }, [visible, text.length, cps, instant]);

  // Listen for the scene-wide "tap fired but bubble is still streaming"
  // signal so the first tap completes the reveal even though it was caught
  // by SceneLayer instead of by us. Second tap then advances normally.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const onReveal = () => setVisible(text.length);
    window.addEventListener("paradise:reveal-all", onReveal);
    return () => window.removeEventListener("paradise:reveal-all", onReveal);
  }, [text.length]);

  return {
    rendered: text.slice(0, visible),
    complete: visible >= text.length,
    revealAll: () => setVisible(text.length),
  };
}
