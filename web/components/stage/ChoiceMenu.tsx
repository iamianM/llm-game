"use client";

import type { AvailableAction } from "../../lib/types";
import { Pill } from "../ui/Pill";

type Props = { actions: AvailableAction[]; locked: boolean; onChoose: (action: AvailableAction) => void };

export function ChoiceMenu({ actions, locked, onChoose }: Props) {
  return (
    <div data-testid="choice-menu" className="mx-auto grid w-full max-w-5xl grid-cols-5 gap-3 px-5 pb-5">
      {actions.slice(0, 5).map((action, index) => {
        const meta = [action.risk, action.stat_used].filter(Boolean).join(" · ");
        return (
          <button
            data-role="choice"
            data-testid="choice"
            disabled={locked}
            key={`${action.kind}-${action.target_id}-${action.intent_id}-${index}`}
            onClick={() => onChoose(action)}
            className="min-h-24 rounded-[var(--r-md)] border border-line bg-card p-3 text-left text-ink shadow-[var(--shadow-sm)] transition hover:-translate-y-0.5 hover:border-accent disabled:opacity-60"
          >
            <div className="mb-2 h-5">
              {action.audience_hint ? <Pill tone={action.audience_hint === "+" ? "good" : "bad"}>Pulse {action.audience_hint}</Pill> : null}
            </div>
            <div className="font-semibold">{action.label}</div>
            {meta ? <div className="mt-2 text-xs text-[var(--muted)]">{meta}</div> : null}
          </button>
        );
      })}
    </div>
  );
}
