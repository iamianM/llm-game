// Canonical NPC standee art, keyed by engine slot_id. One source of truth for
// both the in-scene sprite and the HUD/profile avatar. Every id here has a
// transparent-background webp baked into web/public/images/characters by
// _roster_convert.py. Players never appear here — their art resolves through
// player-sprite.ts from the chosen roster character.
const NPC_SLOT_IDS = [
  // Opening resort cast (6 women + 6 men, incl. heart-throb pool).
  "chloe",
  "maya",
  "sophie",
  "nia",
  "riley_ht",
  "talia_ht",
  "liam",
  "marcus",
  "blake",
  "jordan",
  "sam_ht",
  "ellis_ht",
  // Flush of Hearts arrivals (3 men + 3 women).
  "beau",
  "jules",
  "mateo",
  "sasha",
  "zara",
  "noor",
] as const;

export const NPC_IMAGE_BY_ID: Record<string, string> = Object.fromEntries(
  NPC_SLOT_IDS.map((id) => [id, `/images/characters/${id}.webp`]),
);

/** Resolve an NPC's standee, or undefined for an unknown id (falls back to a monogram). */
export function npcSprite(id: string): string | undefined {
  return NPC_IMAGE_BY_ID[id];
}
