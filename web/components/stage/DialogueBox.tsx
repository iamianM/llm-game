"use client";

import { ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { useUiStore } from "../../lib/store";
import { DeltaChip } from "./DeltaChip";

type Props = {
  speaker: string;
  text: string;
  playerLine?: string;
  complete?: boolean;
  audienceDelta?: number | null;
  audienceReason?: string | null;
  onAdvance?: () => void;
};

export function DialogueBox({ speaker, text, playerLine, complete = true, audienceDelta, audienceReason, onAdvance }: Props) {
  const speed = useUiStore((s) => s.typewriterSpeed);
  const reduce = useUiStore((s) => s.reduceMotion);
  const [visible, setVisible] = useState(text);
  useEffect(() => {
    if (!complete) {
      setVisible(text);
      return;
    }
    if (speed === "instant" || reduce) {
      setVisible(text);
      return;
    }
    setVisible("");
    const interval = speed === "slow" ? 45 : speed === "fast" ? 12 : 24;
    let index = 0;
    const timer = window.setInterval(() => {
      index += 1;
      setVisible(text.slice(0, index));
      if (index >= text.length) window.clearInterval(timer);
    }, interval);
    return () => window.clearInterval(timer);
  }, [text, speed, reduce, complete]);

  function handleClick() {
    if (visible !== text) {
      setVisible(text);
      return;
    }
    if (complete) onAdvance?.();
  }

  return (
    <section onClick={handleClick} className="min-h-[28vh] border-t border-white/10 bg-black/30 p-5">
      <div className="mx-auto max-w-5xl rounded-[var(--r-lg)] border border-line bg-card p-5 text-ink shadow-[var(--shadow-lg)]">
        {playerLine ? <p className="mb-3 text-sm text-[var(--muted)]"><b>You:</b> {playerLine}</p> : null}
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-display text-2xl text-accent">{speaker}</h2>
          <DeltaChip delta={audienceDelta} reason={audienceReason} />
        </div>
        <p aria-live="polite" className="mt-2 min-h-16 text-lg leading-8">{visible || "..."}</p>
        <div data-state={visible === text && complete ? "dialogue-complete" : "dialogue-streaming"} className="mt-2 flex justify-end text-accent">
          {visible === text ? <ChevronRight /> : null}
        </div>
      </div>
    </section>
  );
}
