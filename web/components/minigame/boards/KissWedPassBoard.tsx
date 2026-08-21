import type { KissWedPassBoardView } from "../../../lib/minigame/types";
import { subjectLabel, type SubjectLabels } from "../board-utils";

const ROLES = ["kiss", "wed", "pass"] as const;

export function KissWedPassBoard({
  board,
  subjectLabels,
}: {
  board: KissWedPassBoardView;
  subjectLabels: SubjectLabels;
}) {
  return (
    <div className="allocation-cards">
      {ROLES.map((role) => {
        const allocation = (board.allocations ?? []).find((item) => item.role === role);
        return (
          <div className={allocation ? "is-filled" : ""} key={role}>
            <span className="board-eyebrow">{role}</span>
            <strong>{allocation ? subjectLabel(subjectLabels, allocation.subject_id) : "Unassigned"}</strong>
          </div>
        );
      })}
    </div>
  );
}
