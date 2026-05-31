import { isRosterId, rosterSprite } from "../roster";
import type { Gender } from "../types";
import { OUTFIT_STANDEES } from "./outfit-standees";

const ARCHETYPES = new Set(["heartthrob", "class_clown", "loyal_friend"]);

/**
 * Resolve the in-scene player standee. A roster pick (characterId) is the whole
 * identity, so its single baked standee wins outright. Legacy/checkpoint
 * sessions without a characterId fall back to the archetype+gender art, serving
 * a baked per-outfit variant when one exists so the wardrobe reads in-scene.
 * Vercel-safe (prebaked assets, no runtime image generation).
 */
export function playerSprite(archetypeId: string, gender: Gender, outfit?: string, characterId?: string): string {
  if (isRosterId(characterId)) return rosterSprite(characterId as string);
  const archetype = ARCHETYPES.has(archetypeId) ? archetypeId : "heartthrob";
  if (archetype !== archetypeId && typeof window !== "undefined") {
    console.warn(`Missing player archetype sprite for ${archetypeId}; using heartthrob.`);
  }
  const base = `${archetype}_${gender}`;
  if (outfit && OUTFIT_STANDEES.has(`${base}__${outfit}`)) {
    return `/images/player/${base}__${outfit}.webp`;
  }
  return `/images/player/${base}.webp`;
}

/** True when a baked outfit-variant standee exists (clothes actually change). */
export function hasOutfitStandee(archetypeId: string, gender: Gender, outfit?: string): boolean {
  if (!outfit) return false;
  const archetype = ARCHETYPES.has(archetypeId) ? archetypeId : "heartthrob";
  return OUTFIT_STANDEES.has(`${archetype}_${gender}__${outfit}`);
}
