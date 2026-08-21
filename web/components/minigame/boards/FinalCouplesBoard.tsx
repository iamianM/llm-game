import type { FinalCouplesBoardView } from "../../../lib/minigame/types";

export function FinalCouplesBoard({ board }: { board: FinalCouplesBoardView }) {
  if (board.final_tally === null) {
    return <p className="minigame-empty">Facet scores lock after the last answer.</p>;
  }
  return (
    <div className="facet-scores">
      {board.facets.map((facet) => (
        <div key={facet.facet}>
          <span>{facet.facet}</span>
          <strong>{facet.score}</strong>
        </div>
      ))}
      <b>Total {board.final_tally}</b>
    </div>
  );
}
