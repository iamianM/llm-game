import type { CouplesQuizBoardView } from "../../../lib/minigame/types";

export function CouplesQuizBoard({ board }: { board: CouplesQuizBoardView }) {
  if (board.player_answer === null || board.partner_answer === null || board.aligned === null) {
    return <p className="minigame-empty">Both answers stay hidden until the reveal.</p>;
  }
  return (
    <div className="couples-answers">
      <div><span className="board-eyebrow">You chose</span><strong>{board.player_answer}</strong></div>
      <div><span className="board-eyebrow">Partner chose</span><strong>{board.partner_answer}</strong></div>
      <b className={board.aligned ? "is-positive" : "is-negative"}>
        {board.aligned ? "Matched" : "Missed"}
      </b>
    </div>
  );
}
