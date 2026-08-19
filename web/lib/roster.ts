// Playable roster — the pre-made heartbreakers the player picks from in place of
// the old build-your-own creator. Picking one sets *everything*: gender, a
// fixed name, the in-scene standee art, and a preset look recipe (so the HUD
// crest, couple chips and outfit aura all read correctly). There is no text
// entry and no per-field customization — a pick is the whole identity.
//
// These ids never overlap the NPC cast (see scene/npc-art.ts): the player is
// always someone Sunset Bay hasn't met as an NPC. Standee art lives at
// /images/player/roster_<id>.webp, baked by _roster_convert.py.

import type { ArchetypeId, HeartbreakerLook } from "./look";
import type { Gender } from "./types";

export type RosterCharacter = {
  id: string;
  name: string;
  gender: Gender;
  archetype: ArchetypeId;
  /** One-line casting-card hook. */
  tagline: string;
  /** Preset look fields — must reference ids in look.ts catalogs. */
  skinTone: string;
  hairColor: string;
  outfit: string;
  vibe: string;
  accessories: string[];
};

export const ROSTER: RosterCharacter[] = [
  {
    id: "tasha",
    name: "Tasha",
    gender: "woman",
    archetype: "heartthrob",
    tagline: "Gold-standard confidence, walks in knowing the room is hers.",
    skinTone: "tan",
    hairColor: "brown",
    outfit: "finale",
    vibe: "mysterious",
    accessories: ["gold-hoops", "necklace"],
  },
  {
    id: "birdie",
    name: "Birdie",
    gender: "woman",
    archetype: "class_clown",
    tagline: "Sunshine-yellow chaos, turns every silence into a bit.",
    skinTone: "golden",
    hairColor: "blonde",
    outfit: "challenge",
    vibe: "chaos",
    accessories: ["anklet"],
  },
  {
    id: "noa",
    name: "Noa",
    gender: "woman",
    archetype: "loyal_friend",
    tagline: "Linen-and-sun-hat steady, the one everyone trusts first.",
    skinTone: "fair",
    hairColor: "brown",
    outfit: "arrival",
    vibe: "sweet",
    accessories: ["sun-hat"],
  },
  {
    id: "deon",
    name: "Deon",
    gender: "man",
    archetype: "heartthrob",
    tagline: "Crisp linen and a gold watch — effortless main-character energy.",
    skinTone: "rich",
    hairColor: "black",
    outfit: "arrival",
    vibe: "sharp",
    accessories: ["watch"],
  },
  {
    id: "charlie",
    name: "Charlie",
    gender: "man",
    archetype: "class_clown",
    tagline: "Camp-shirt charm, never met a joke he wouldn't commit to.",
    skinTone: "tan",
    hairColor: "chestnut",
    outfit: "party",
    vibe: "sunny",
    accessories: ["sunglasses"],
  },
  {
    id: "theo",
    name: "Theo",
    gender: "man",
    archetype: "loyal_friend",
    tagline: "Coral-shorts easy, the calm anchor in any couple.",
    skinTone: "golden",
    hairColor: "chestnut",
    outfit: "pool",
    vibe: "sporty",
    accessories: [],
  },
];

const ROSTER_BY_ID = new Map(ROSTER.map((c) => [c.id, c]));

export function findRosterCharacter(id: string | undefined): RosterCharacter | undefined {
  return id ? ROSTER_BY_ID.get(id) : undefined;
}

export function isRosterId(id: string | undefined): boolean {
  return !!id && ROSTER_BY_ID.has(id);
}

/** Full standee art path for a roster character. */
export function rosterSprite(id: string): string {
  return `/images/player/roster_${id}.webp`;
}

/** Materialize the full look recipe a roster pick commits to the session. */
export function rosterLook(character: RosterCharacter): HeartbreakerLook {
  return {
    name: character.name,
    gender: character.gender,
    archetype: character.archetype,
    skinTone: character.skinTone,
    hairColor: character.hairColor,
    outfit: character.outfit,
    accessories: character.accessories,
    vibe: character.vibe,
    characterId: character.id,
  };
}
