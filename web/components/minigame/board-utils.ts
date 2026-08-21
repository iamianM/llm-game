export type SubjectLabels = Readonly<Record<string, string>>;

export function subjectLabel(labels: SubjectLabels, subjectId: string) {
  const label = labels[subjectId];
  if (label === undefined) {
    throw new Error(`Missing player-facing label for minigame subject ${subjectId}.`);
  }
  return label;
}
