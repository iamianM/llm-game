import type { Position } from "./types";

export const PLAYER_ANCHOR: Position = { x: 50, y: 92, scale: 1 };

const WIDE_LAYOUTS: Position[][] = [
  [],
  [{ x: 50, y: 52, scale: 1 }],
  [
    { x: 34, y: 53, scale: 0.94 },
    { x: 66, y: 53, scale: 0.94 },
  ],
  [
    { x: 26, y: 54, scale: 0.88 },
    { x: 50, y: 50, scale: 0.94 },
    { x: 74, y: 54, scale: 0.88 },
  ],
  [
    { x: 22, y: 55, scale: 0.82 },
    { x: 40, y: 51, scale: 0.9 },
    { x: 60, y: 51, scale: 0.9 },
    { x: 78, y: 55, scale: 0.82 },
  ],
];

export function npcPositions(count: number, focusedIndex: number | null): Position[] {
  if (count <= 0) return [];
  if (focusedIndex === null || focusedIndex < 0 || focusedIndex >= count) return widePositions(count);

  // When a target is in focus, give the stage to them + at most two flanking
  // peers (one left, one right). Everyone else is pushed off-stage so the
  // scene reads as a focused two-shot, not a crowd.
  return Array.from({ length: count }, (_, index) => {
    if (index === focusedIndex) return { x: 50, y: 48, scale: 1.08 };
    const sideIndex = index < focusedIndex ? index : index - 1;
    if (sideIndex === 0) return { x: 18, y: 56, scale: 0.74, dimmed: true };
    if (sideIndex === 1) return { x: 82, y: 56, scale: 0.74, dimmed: true };
    // Past the first flanker on each side, hide off-stage.
    return { x: 50, y: 56, scale: 0.7, dimmed: true, hidden: true };
  });
}

function widePositions(count: number): Position[] {
  const preset = WIDE_LAYOUTS[count];
  if (preset) return preset;
  const startX = 12;
  const endX = 88;
  const span = endX - startX;
  return Array.from({ length: count }, (_, index) => ({
    x: startX + (span / Math.max(1, count - 1)) * index,
    y: 53 + (index % 3) * 2,
    scale: count > 10 ? 0.62 : count > 6 ? 0.7 : 0.78,
  }));
}
