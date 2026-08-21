import type { CompatibilityQuizBoardView } from "../../../lib/minigame/types";

export function CompatibilityQuizBoard({ board }: { board: CompatibilityQuizBoardView }) {
  const answer = board.latest_answer;
  if (!answer) {
    return <p className="minigame-empty">Your first answer will turn over here.</p>;
  }
  return (
    <div className={`answer-reveal ${answer.is_correct ? "is-positive" : "is-negative"}`}>
      <span className="board-eyebrow">Your answer</span>
      <strong>{answer.chosen_label}</strong>
      {!answer.is_correct && answer.correct_label ? <span>Correct answer: {answer.correct_label}</span> : null}
      {answer.reaction_line ? <q>{answer.reaction_line}</q> : null}
    </div>
  );
}
