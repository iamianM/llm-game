"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { SceneFrame, ScenePlan } from "../../lib/scene/presentation";
import type { SceneBeat } from "../../lib/scene/types";

type PlaybackItem<TSlot> = {
  id: string;
  beat: SceneBeat;
  frame: SceneFrame;
  slot: TSlot | null;
};

export function useScenePlayback<TSlot>(plan: ScenePlan<TSlot>) {
  const items = useMemo(() => flattenPlan(plan), [plan]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [settled, setSettled] = useState(false);
  const planId = useRef(plan.id);
  const lastCompletedId = useRef<string | null>(null);

  useEffect(() => {
    if (planId.current !== plan.id) {
      planId.current = plan.id;
      lastCompletedId.current = null;
      setActiveIndex(0);
      setSettled(false);
      return;
    }
    if (!lastCompletedId.current) return;
    const completedIndex = items.findIndex((item) => item.id === lastCompletedId.current);
    if (completedIndex >= 0) {
      setActiveIndex(Math.min(completedIndex + 1, Math.max(0, items.length - 1)));
      if (completedIndex + 1 < items.length) setSettled(false);
    }
  }, [items, plan.id]);

  const activeItem = items[Math.min(activeIndex, Math.max(0, items.length - 1))];
  const advance = useCallback(() => {
    if (!activeItem || activeItem.beat.kind === "choice_fan") return;
    if (revealStreamingBubble()) return;
    lastCompletedId.current = activeItem.id;
    if (activeIndex >= items.length - 1) {
      setSettled(true);
      return;
    }
    setActiveIndex((index) => Math.min(index + 1, items.length - 1));
  }, [activeIndex, activeItem, items.length]);

  useEffect(() => {
    if (!activeItem || activeItem.beat.kind === "choice_fan") setSettled(true);
  }, [activeItem]);

  return {
    activeBeat: activeItem?.beat,
    activeFrame: activeItem?.frame,
    activeSlot: activeItem?.slot ?? null,
    activeIndex,
    advance,
    hasLaterBeat: activeIndex < items.length - 1,
    items,
    settled,
  };
}

export function flattenPlan<TSlot>(plan: ScenePlan<TSlot>): PlaybackItem<TSlot>[] {
  const items: PlaybackItem<TSlot>[] = [];
  const occurrence = new Map<string, number>();
  let frameIndex = 0;

  for (const segment of plan.segments) {
    for (const beat of segment.beats) {
      const base = beatIdentity(beat);
      const ordinal = occurrence.get(`${segment.id}:${base}`) ?? 0;
      occurrence.set(`${segment.id}:${base}`, ordinal + 1);
      const frame = plan.frames[frameIndex];
      if (!frame) throw new Error(`Scene plan ${plan.id} is missing frame ${frameIndex}.`);
      items.push({
        id: `${segment.id}:${base}:${ordinal}`,
        beat,
        frame,
        slot: segment.slot,
      });
      frameIndex += 1;
    }
  }

  if (frameIndex !== plan.frames.length) {
    throw new Error(`Scene plan ${plan.id} has ${plan.frames.length} frames for ${frameIndex} beats.`);
  }
  return items;
}

function beatIdentity(beat: SceneBeat): string {
  switch (beat.kind) {
    case "camera":
      return `camera:${beat.shot}:${beat.focusIds.join(",")}`;
    case "speech":
      return `speech:${beat.speakerId}`;
    case "narrator":
      return `narrator:${beat.sourceEventId ?? "event"}`;
    case "reaction":
      return `reaction:${beat.reactorId}`;
    case "choice_fan":
      return "choice_fan";
    case "delta_pop":
      return `delta:${beat.subjectId}:${beat.deltaKind}`;
    case "connection_shift":
      return `connection:${beat.subjectId}`;
  }
}

function revealStreamingBubble(): boolean {
  if (typeof document === "undefined") return false;
  const streaming = document.querySelector(
    '[data-testid="speech-bubble"][data-stream-complete="false"], ' +
      '[data-testid="player-bubble"][data-stream-complete="false"], ' +
      '[data-testid="narrator-bubble"][data-stream-complete="false"]',
  );
  if (!streaming) return false;
  window.dispatchEvent(new CustomEvent("paradise:reveal-all"));
  return true;
}
