import type { Position } from "./types";

// The player sits bottom-LEFT and always reads as the foreground figure —
// the Love Island mobile framing where "you" are closest to camera while the
// rest of the villa is staged above/behind. Feet park just BELOW the frame so
// the figure crops at the shin and reads large + close (the real size comes
// from the tall is-player CSS box in CharacterSprite).
export const PLAYER_ANCHOR: Position = { x: 22, y: 105, scale: 1.16 };

// When the player's choice fan is open the option bars overlay the lower body
// (Love Island lets the cards sit over the legs, faces still showing) — so the
// player barely changes: a hair smaller/left so the cards have breathing room.
export const PLAYER_ANCHOR_COMPACT: Position = { x: 20, y: 104, scale: 1.0 };

// The spotlight slot: whoever is speaking / in focus strides to centre-front,
// large and close, feet just under the frame so they crop thigh-up like the
// Love Island "to camera" hero. Everyone else recedes into a tighter, softly
// blurred cluster just behind so the eye still lands on the talker.
const SPOTLIGHT: Position = { x: 58, y: 101, scale: 1.32 };

// Upstage cluster for the non-focused cast: packed close just behind the
// speaker (not a distant line), dimmed + blurred by CharacterSprite so they
// read as "the rest of the villa right there behind you".
const BACKROW_Y = 66;
const BACKROW_SCALE = 0.84;

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
  if (total <= 1) return { x: 26, y: BACKROW_Y, scale: BACKROW_SCALE, dimmed: true };
  // Pack the cluster across the upper-left/centre band behind the spotlight
  // (which owns the right-of-centre). Keep them off the far edges so they read
  // as a tight group standing just behind, not a thin line across the room.
  const startX = 14;
  const endX = 84;
  const x = startX + ((endX - startX) / (total - 1)) * rank;
  // Stagger depth a touch so the cluster isn't a flat cardboard line.
  const y = BACKROW_Y + (rank % 2) * 4;
  return { x, y, scale: BACKROW_SCALE, dimmed: true };
}

function ensemble(count: number): Position[] {
  const preset = ENSEMBLE_LAYOUTS[count];
  if (preset) return preset;
  const startX = 14;
  const endX = 86;
  const span = endX - startX;
  // Sit the crowd low in the frame (feet near the bottom) so they crop thigh-up
  // and fill the stage like a packed villa, instead of hovering mid-screen with
  // dead air above their heads.
  return Array.from({ length: count }, (_, index) => ({
    x: startX + (span / Math.max(1, count - 1)) * index,
    y: 90 + (index % 3) * 3,
    scale: count > 9 ? 0.84 : count > 6 ? 0.94 : 1.04,
  }));
}

// Hand-tuned arcs for small ensembles (the firepit ring before anyone speaks).
// Feet park low so the figures read big and close, Love Island style.
const ENSEMBLE_LAYOUTS: Position[][] = [
  [],
  [{ x: 50, y: 102, scale: 1.32 }],
  [
    { x: 36, y: 100, scale: 1.16 },
    { x: 66, y: 102, scale: 1.2 },
  ],
  [
    { x: 27, y: 96, scale: 1.04 },
    { x: 51, y: 102, scale: 1.2 },
    { x: 75, y: 97, scale: 1.06 },
  ],
  [
    { x: 23, y: 93, scale: 0.98 },
    { x: 43, y: 100, scale: 1.14 },
    { x: 64, y: 100, scale: 1.14 },
    { x: 83, y: 93, scale: 0.98 },
  ],
];
