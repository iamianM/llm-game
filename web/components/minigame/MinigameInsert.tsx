"use client";

import type { MinigamePresentation } from "../../lib/minigame/presentation";
import type { SubjectLabels } from "./board-utils";
import { MinigameBoard } from "./MinigameBoard";

export function MinigameInsert({
  presentation,
  subjectLabels,
}: {
  presentation: MinigamePresentation;
  subjectLabels: SubjectLabels;
}) {
  return (
    <section className="minigame-insert" data-testid="minigame-insert" data-minigame-kind={presentation.board.kind}>
      <header>
        <div>
          <span>{presentation.kicker}</span>
          <h2>{presentation.title}</h2>
        </div>
        <b>{presentation.roundLabel}</b>
        <i aria-hidden><span style={{ width: `${presentation.progressPercent}%` }} /></i>
      </header>
      {presentation.question ? <p className="minigame-question">{presentation.question}</p> : null}
      <MinigameBoard board={presentation.board} subjectLabels={subjectLabels} />
      <style jsx>{`
        .minigame-insert {
          width: min(560px, calc(100vw - 24px));
          display: grid;
          gap: 10px;
          padding: 12px 14px 14px;
          border: 1px solid rgba(217,167,58,.42);
          border-radius: var(--r-lg);
          background: rgba(20,16,12,.84);
          box-shadow: var(--shadow-md), var(--inset-gold);
          color: var(--card);
          backdrop-filter: blur(9px);
        }
        header {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 5px 12px;
          align-items: end;
        }
        header div { display: grid; gap: 1px; }
        header span {
          color: var(--gold-soft);
          font-size: 10px;
          font-weight: 800;
          letter-spacing: .13em;
          text-transform: uppercase;
        }
        h2 { margin: 0; font-family: var(--font-display); font-size: 22px; line-height: 1; }
        header b { color: var(--muted-on-dark); font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }
        header > i {
          grid-column: 1 / -1;
          display: block;
          height: 3px;
          overflow: hidden;
          border-radius: var(--r-pill);
          background: rgba(217,167,58,.14);
        }
        header > i span {
          display: block;
          height: 100%;
          border-radius: inherit;
          background: linear-gradient(90deg, var(--accent), var(--gold));
        }
        .minigame-question {
          margin: 0;
          color: var(--card);
          font-family: var(--font-display);
          font-size: 15px;
          line-height: 1.3;
          text-align: center;
        }
        @media (max-width: 520px), (max-height: 720px) {
          .minigame-insert { gap: 8px; padding: 9px 10px 11px; }
          h2 { font-size: 18px; }
          .minigame-question { font-size: 13px; }
        }
      `}</style>
    </section>
  );
}
