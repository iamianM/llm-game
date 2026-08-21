import type { LieDetectorBoardView } from "../../../lib/minigame/types";
import { subjectLabel, type SubjectLabels } from "../board-utils";

const VERDICT_LABELS = {
  truth_told: "Truth verified",
  truth_suspected: "Truth suspected",
  lie_caught: "Lie caught",
  lie_believed: "Lie believed",
} satisfies Record<NonNullable<LieDetectorBoardView["verdict"]>, string>;

export function LieDetectorBoard({
  board,
  subjectLabels,
}: {
  board: LieDetectorBoardView;
  subjectLabels: SubjectLabels;
}) {
  if (board.subject_id === null || board.verdict === null || board.needle_percent === null) {
    return <p className="minigame-empty">The needle is waiting for a recorded result.</p>;
  }
  return (
    <div className="detector-result">
      <span className="board-eyebrow">{subjectLabel(subjectLabels, board.subject_id)}</span>
      <div className="detector-track" aria-label={`Recorded needle value ${board.needle_percent}`}>
        <i style={{ left: `${board.needle_percent}%` }} />
      </div>
      <strong>{VERDICT_LABELS[board.verdict]}</strong>
    </div>
  );
}
