import type { Gender } from "../types";

const ARCHETYPES = new Set(["heartthrob", "class_clown", "loyal_friend"]);

export function playerSprite(archetypeId: string, gender: Gender): string {
  const archetype = ARCHETYPES.has(archetypeId) ? archetypeId : "heartthrob";
  if (archetype !== archetypeId && typeof window !== "undefined") {
    console.warn(`Missing player archetype sprite for ${archetypeId}; using heartthrob.`);
  }
  return `/images/player/${archetype}_${gender}.webp`;
}
