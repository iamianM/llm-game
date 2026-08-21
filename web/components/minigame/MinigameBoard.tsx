"use client";

import type { ReactNode } from "react";
import type { MinigameBoardView, MinigameKind } from "../../lib/minigame/types";
import { type SubjectLabels } from "./board-utils";
import { CompatibilityQuizBoard } from "./boards/CompatibilityQuizBoard";
import { CouplesQuizBoard } from "./boards/CouplesQuizBoard";
import { FinalCouplesBoard } from "./boards/FinalCouplesBoard";
import { KissWedPassBoard } from "./boards/KissWedPassBoard";
import { LieDetectorBoard } from "./boards/LieDetectorBoard";
import { PulseRaceBoard } from "./boards/PulseRaceBoard";

type BoardRenderer = (board: MinigameBoardView, subjectLabels: SubjectLabels) => ReactNode;

const BOARD_RENDERERS = {
  compatibility_quiz: (board) => {
    if (board.kind !== "compatibility_quiz") throw new Error("Compatibility Quiz renderer received another board kind.");
    return <CompatibilityQuizBoard board={board} />;
  },
  heart_rate: (board, subjectLabels) => {
    if (board.kind !== "heart_rate") throw new Error("Pulse Race renderer received another board kind.");
    return <PulseRaceBoard board={board} subjectLabels={subjectLabels} />;
  },
  couples_quiz: (board) => {
    if (board.kind !== "couples_quiz") throw new Error("Couples Quiz renderer received another board kind.");
    return <CouplesQuizBoard board={board} />;
  },
  lie_detector: (board, subjectLabels) => {
    if (board.kind !== "lie_detector") throw new Error("Lie Detector renderer received another board kind.");
    return <LieDetectorBoard board={board} subjectLabels={subjectLabels} />;
  },
  kiss_wed_pass: (board, subjectLabels) => {
    if (board.kind !== "kiss_wed_pass") throw new Error("Kiss Wed Pass renderer received another board kind.");
    return <KissWedPassBoard board={board} subjectLabels={subjectLabels} />;
  },
  final_couples: (board) => {
    if (board.kind !== "final_couples") throw new Error("Final Couples renderer received another board kind.");
    return <FinalCouplesBoard board={board} />;
  },
} satisfies Record<MinigameKind, BoardRenderer>;

/** Stable inspection surface for contract tests; rendering still goes through the exhaustive registry. */
export const MINIGAME_BOARD_KINDS = Object.freeze(Object.keys(BOARD_RENDERERS) as MinigameKind[]);

export function MinigameBoard({
  board,
  subjectLabels,
}: {
  board: MinigameBoardView;
  subjectLabels: SubjectLabels;
}) {
  return (
    <div className="minigame-board" data-testid="minigame-board" data-board-kind={board.kind}>
      {BOARD_RENDERERS[board.kind](board, subjectLabels)}
      <style jsx global>{`
        .minigame-board {
          width: 100%;
          color: var(--card);
        }
        .minigame-board .minigame-empty {
          margin: 0;
          color: var(--muted-on-dark);
          font-size: 13px;
          text-align: center;
        }
        .minigame-board .board-eyebrow {
          color: var(--gold-soft);
          font-size: 10px;
          font-weight: 800;
          letter-spacing: .12em;
          text-transform: uppercase;
        }
        .minigame-board .answer-reveal {
          display: grid;
          gap: 4px;
          text-align: center;
        }
        .minigame-board .answer-reveal strong { font-family: var(--font-display); font-size: 20px; }
        .minigame-board .answer-reveal q { color: var(--muted-on-dark); font-style: italic; }
        .minigame-board .is-positive { color: #a9d69f; }
        .minigame-board .is-negative { color: #f1a38f; }
        .minigame-board .couples-answers {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
          text-align: center;
        }
        .minigame-board .couples-answers > div {
          display: grid;
          gap: 3px;
          padding: 8px;
          border-radius: var(--r-md);
          background: rgba(248,236,210,.06);
        }
        .minigame-board .couples-answers b { grid-column: 1 / -1; }
        .minigame-board .pulse-readings { display: grid; gap: 6px; }
        .minigame-board .pulse-reading {
          display: grid;
          grid-template-columns: minmax(120px, 1fr) minmax(70px, 1fr) auto;
          gap: 8px;
          align-items: center;
          font-size: 12px;
        }
        .minigame-board .pulse-reading i {
          display: block;
          height: 5px;
          max-width: 100%;
          border-radius: var(--r-pill);
          background: linear-gradient(90deg, var(--accent), var(--gold-soft));
        }
        .minigame-board .detector-result { display: grid; gap: 8px; text-align: center; }
        .minigame-board .detector-track {
          position: relative;
          height: 8px;
          border-radius: var(--r-pill);
          background: linear-gradient(90deg, rgba(91,124,79,.6), rgba(217,167,58,.55), rgba(193,75,58,.65));
        }
        .minigame-board .detector-track i {
          position: absolute;
          top: 50%;
          width: 3px;
          height: 18px;
          transform: translate(-50%, -50%);
          border-radius: var(--r-pill);
          background: var(--card);
          box-shadow: 0 0 9px var(--gold-glow);
        }
        .minigame-board .allocation-cards {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 7px;
        }
        .minigame-board .allocation-cards > div {
          display: grid;
          gap: 5px;
          min-height: 54px;
          place-content: center;
          border: 1px solid rgba(217,167,58,.22);
          border-radius: var(--r-md);
          color: var(--muted-on-dark);
          text-align: center;
        }
        .minigame-board .allocation-cards > .is-filled {
          border-color: rgba(217,167,58,.62);
          color: var(--card);
          background: rgba(217,167,58,.08);
        }
        .minigame-board .facet-scores {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 6px;
          text-align: center;
        }
        .minigame-board .facet-scores > div {
          display: grid;
          gap: 2px;
          padding: 6px 4px;
          border-radius: var(--r-sm);
          background: rgba(248,236,210,.06);
        }
        .minigame-board .facet-scores span { font-size: 10px; text-transform: capitalize; }
        .minigame-board .facet-scores b { grid-column: 1 / -1; color: var(--gold-soft); }
        @media (max-width: 520px) {
          .minigame-board .pulse-reading { grid-template-columns: 1fr auto; }
          .minigame-board .pulse-reading i { grid-column: 1 / -1; grid-row: 2; }
          .minigame-board .facet-scores { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        }
      `}</style>
    </div>
  );
}
