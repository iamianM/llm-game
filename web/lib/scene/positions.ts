import type { Position } from "./types";

// The player sits bottom-LEFT and always reads as the foreground figure —
// the Love Island mobile framing where "you" are closest to camera while the
// rest of the villa is staged above/behind. Anchored low + large (final size
// also comes from the bigger is-player CSS box in CharacterSprite).
export const PLAYER_ANCHOR: Position = { x: 19, y: 99, scale: 1.16 };

// When the player's choice fan is open the options dock along the bottom; on
// mobile that bar would sit right on top of a bottom-left standee. The sprite
// shrinks + lifts (mobile via CSS) so the figure tucks above the options.
export const PLAYER_ANCHOR_COMPACT: Position = { x: 17, y: 99, scale: 0.96 };

// The spotlight slot: whoever is speaking / in focus strides to centre-front
// at full size and owns the frame. Everyone else recedes into a softly blurred
// upstage band so the eye lands on the talker (Love Island's "to camera" look).
const SPOTLIGHT: Position = { x: 55, y: 80, scale: 1.34 };

// Upstage band for the non-focused cast: small, pushed to the back, dimmed +
// blurred by CharacterSprite so they read as "the rest of the villa behind".
const BACKROW_Y = 43;
const BACKROW_SCALE = 0.56;

export function npcPositions(count: number, focusedIndex: number | null): Position[] {
  if (count <= 0) return [];

  // No single focus (idle / ceremony / wide camera beat) → spread the cast in
  // a gentle arc across mid-stage so the villa feels populated.
  if (focusedIndex === null || focusedIndex < 0 || focusedIndex >= count) {
    return ensemble(count);
  }

  // Focus → spotlight the speaker centre-front, recede the rest upstage.
  const others = count - 1;
  const positions: Position[] = [];
  let rank = 0;
  for (let index = 0; index < count; index += 1) {
    if (index === focusedIndex) {
      positions.push({ ...SPOTLIGHT });
    } else {
      positions.push(backRowSlot(rank, others));
      rank += 1;
    }
  }
  return positions;
}

function backRowSlot(rank: number, total: number): Position {
  if (total <= 1) return { x: 80, y: BACKROW_Y, scale: BACKROW_SCALE, dimmed: true };
  const startX = 12;
  const endX = 88;
  const x = startX + ((endX - startX) / (total - 1)) * rank;
  // Stagger depth a touch so the back row isn't a flat cardboard line.
  const y = BACKROW_Y + (rank % 2) * 3;
  return { x, y, scale: BACKROW_SCALE, dimmed: true };
}

function ensemble(count: number): Position[] {
  const preset = ENSEMBLE_LAYOUTS[count];
  if (preset) return preset;
  const startX = 12;
  const endX = 88;
  const span = endX - startX;
  return Array.from({ length: count }, (_, index) => ({
    x: startX + (span / Math.max(1, count - 1)) * index,
    y: 56 + (index % 3) * 2,
    scale: count > 9 ? 0.62 : count > 6 ? 0.7 : 0.78,
  }));
}

// Hand-tuned arcs for small ensembles (the firepit ring before anyone speaks).
const ENSEMBLE_LAYOUTS: Position[][] = [
  [],
  [{ x: 52, y: 70, scale: 1.1 }],
  [
    { x: 36, y: 64, scale: 0.92 },
    { x: 66, y: 64, scale: 0.92 },
  ],
  [
    { x: 28, y: 60, scale: 0.84 },
    { x: 52, y: 66, scale: 0.96 },
    { x: 76, y: 60, scale: 0.84 },
  ],
  [
    { x: 24, y: 58, scale: 0.78 },
    { x: 43, y: 63, scale: 0.9 },
    { x: 63, y: 63, scale: 0.9 },
    { x: 82, y: 58, scale: 0.78 },
  ],
];
