import type { Position } from "./types";

// The player sits bottom-LEFT and always reads as the foreground figure —
// the Love Island mobile framing where "you" are closest to camera while the
// rest of the villa is staged above/behind. Anchored low and slightly larger
// than the ring so they sit in front (z-index handled in CharacterSprite).
export const PLAYER_ANCHOR: Position = { x: 21, y: 99, scale: 1.16 };

// Wide-group positions — the firepit ring. Used during intros, ceremonies,
// idle scenes, and as the *base* layout for focused conversations (we
// nudge the focused islander forward but keep everyone else right where
// they were so the ring stays intact).
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

// Tuning constants for the "emphasize the speaker without hiding the rest"
// composition. The focused islander gets a step forward + a scale bump; the
// rest stay in their wide_group slot, just slightly dimmed so the eye knows
// where to look.
const FOCUS_Y_OFFSET = 4;     // pull focused NPC forward in the scene
const FOCUS_SCALE_BONUS = 0.18; // bump scale on top of the wide-group base
const UNFOCUSED_OPACITY_HINT = true; // dim the rest via the dimmed flag

export function npcPositions(count: number, focusedIndex: number | null): Position[] {
  if (count <= 0) return [];
  const base = widePositions(count);
  if (focusedIndex === null || focusedIndex < 0 || focusedIndex >= count) return base;

  return base.map((position, index) => {
    if (index === focusedIndex) {
      // Pull the speaker forward + scale them up. We keep their x so the
      // ring composition doesn't shuffle every focus change.
      return {
        x: position.x,
        y: Math.max(40, position.y - FOCUS_Y_OFFSET),
        scale: position.scale + FOCUS_SCALE_BONUS,
      };
    }
    // Everyone else stays put but reads as "background" — dimmed so the
    // focused one pops, no longer hidden off-stage.
    return {
      ...position,
      dimmed: UNFOCUSED_OPACITY_HINT,
    };
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
