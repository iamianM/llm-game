import type { PulseRaceBoardView } from "../../../lib/minigame/types";
import { subjectLabel, type SubjectLabels } from "../board-utils";

export function PulseRaceBoard({
  board,
  subjectLabels,
}: {
  board: PulseRaceBoardView;
  subjectLabels: SubjectLabels;
}) {
  const readings = board.readings ?? [];
  if (readings.length === 0) {
    return <p className="minigame-empty">The monitors reveal their readings after the final pick.</p>;
  }
  return (
    <div className="pulse-readings">
      {readings.map((reading) => (
        <div className="pulse-reading" key={`${reading.performer_id}:${reading.observer_id}`}>
          <span>{subjectLabel(subjectLabels, reading.performer_id)} for {subjectLabel(subjectLabels, reading.observer_id)}</span>
          <i aria-hidden style={{ width: `${reading.bpm}%` }} />
          <strong>{reading.bpm} BPM</strong>
        </div>
      ))}
    </div>
  );
}
