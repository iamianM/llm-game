import type { Position } from "./types";

export const PLAYER_ANCHOR: Position = { x: 50, y: 88, scale: 1 };

const WIDE_LAYOUTS: Position[][] = [
  [],
  [{ x: 50, y: 55, scale: 1 }],
  [
    { x: 35, y: 55, scale: 0.96 },
    { x: 65, y: 55, scale: 0.96 },
  ],
  [
    { x: 28, y: 56, scale: 0.9 },
    { x: 50, y: 53, scale: 0.96 },
    { x: 72, y: 56, scale: 0.9 },
  ],
  [
    { x: 24, y: 57, scale: 0.84 },
    { x: 42, y: 54, scale: 0.92 },
    { x: 58, y: 54, scale: 0.92 },
    { x: 76, y: 57, scale: 0.84 },
  ],
];

export function npcPositions(count: number, focusedIndex: number | null): Position[] {
  if (count <= 0) return [];
  if (focusedIndex === null || focusedIndex < 0 || focusedIndex >= count) return widePositions(count);

  const positions = widePositions(count);
  return positions.map((position, index) => {
    if (index === focusedIndex) return { x: count === 1 ? 50 : 39, y: 51, scale: 1.1 };
    const sideIndex = index < focusedIndex ? index : index - 1;
    const clumpY = 56 + (sideIndex % 3) * 3;
    const clumpX = 72 + (sideIndex % 2) * 9;
    return {
      x: Math.min(88, clumpX),
      y: Math.min(66, clumpY),
      scale: Math.max(0.68, 0.82 - sideIndex * 0.03),
      dimmed: true,
    };
  });
}

function widePositions(count: number): Position[] {
  const preset = WIDE_LAYOUTS[count];
  if (preset) return preset;
  const capped = count;
  const startX = 18;
  const endX = 82;
  const span = endX - startX;
  return Array.from({ length: capped }, (_, index) => ({
    x: startX + (span / Math.max(1, capped - 1)) * index,
    y: 56 + (index % 3) * 2,
    scale: count > 10 ? 0.62 : 0.72,
    dimmed: count > 8,
  }));
}
