// Player appearance ("look") model + catalog + persistence.
//
// Personalization is intentionally Vercel-safe: nothing here calls an image
// API at runtime. A look is a small structured recipe persisted in
// localStorage (the same place sessions live today). The in-scene player
// sprite stays the prebaked photoreal `{archetype}_{gender}` standee; the
// look layers styling on top of it (outfit palette accent, accessory badges,
// chosen name) and can opt into a look-specific sprite when one exists.
//
// When accounts ship, this recipe syncs to the server alongside the session
// blob without touching call sites.

import type { Gender } from "./types";

export type ArchetypeId = "heartthrob" | "class_clown" | "loyal_friend";

export type IslanderLook = {
  name: string;
  gender: Gender;
  archetype: ArchetypeId;
  skinTone: string; // SKIN_TONES id
  hairColor: string; // HAIR_COLORS id
  outfit: string; // OUTFITS id
  accessories: string[]; // ACCESSORIES ids (multi-select)
  vibe: string; // VIBES id
};

export type SwatchOption = {
  id: string;
  label: string;
  detail: string;
  value: string; // CSS color
};

export type OutfitOption = {
  id: string;
  label: string;
  category: string;
  detail: string;
  primary: string;
  secondary: string;
  accent: string;
};

export type AccessoryOption = {
  id: string;
  label: string;
  slot: string;
  /** lucide-react icon name rendered as a badge on the avatar/chip. */
  icon: string;
};

export type ArchetypeOption = {
  id: ArchetypeId;
  label: string;
  bonus: string;
  detail: string;
};

export const ARCHETYPES: ArchetypeOption[] = [
  { id: "heartthrob", label: "Heartthrob", bonus: "+3 Charm", detail: "Walk in with instant spark and magnetic eye contact." },
  { id: "class_clown", label: "Class Clown", bonus: "+3 Banter", detail: "Quick jokes, warm timing, the crowd-pleaser edge." },
  { id: "loyal_friend", label: "Loyal Friend", bonus: "+3 Loyalty", detail: "Steadier bonds and a real, trusted reputation." },
];

export const SKIN_TONES: SwatchOption[] = [
  { id: "deep", label: "Deep", detail: "Deep brown", value: "#5a3826" },
  { id: "rich", label: "Rich", detail: "Rich brown", value: "#7a4a2f" },
  { id: "tan", label: "Tan", detail: "Warm tan", value: "#b07a4f" },
  { id: "olive", label: "Olive", detail: "Sun-kissed olive", value: "#c69465" },
  { id: "golden", label: "Golden", detail: "Golden beige", value: "#d9a878" },
  { id: "fair", label: "Fair", detail: "Fair", value: "#e9c4a0" },
];

export const HAIR_COLORS: SwatchOption[] = [
  { id: "black", label: "Black", detail: "Jet black", value: "#1c1714" },
  { id: "brown", label: "Brown", detail: "Dark brown", value: "#4a2f1d" },
  { id: "chestnut", label: "Chestnut", detail: "Warm chestnut", value: "#6e3f25" },
  { id: "copper", label: "Copper", detail: "Copper red", value: "#a8502a" },
  { id: "blonde", label: "Blonde", detail: "Honey blonde", value: "#c79a4e" },
  { id: "platinum", label: "Platinum", detail: "Icy platinum", value: "#d9cdb4" },
];

export const VIBES: SwatchOption[] = [
  { id: "sunny", label: "Sunny", detail: "Golden-retriever warmth", value: "#f2b441" },
  { id: "mysterious", label: "Mysterious", detail: "Cool, unreadable confidence", value: "#6f4ca0" },
  { id: "chaos", label: "Chaos", detail: "Glamorous chaos energy", value: "#d94f43" },
  { id: "sweet", label: "Sweet", detail: "Guarded romantic", value: "#e08aa0" },
  { id: "sporty", label: "Sporty", detail: "Competitive spark", value: "#2fa37c" },
  { id: "sharp", label: "Sharp", detail: "Sarcastic charm", value: "#3f7fb0" },
];

// Outfit palettes drive the casting-card backdrop + accent ring. `category`
// hints which scene the look reads best in. These are deliberately the same
// named looks used across the villa (pool / date / party / etc.).
export const OUTFITS: OutfitOption[] = [
  { id: "arrival", label: "Arrival Linen", category: "Arrival", detail: "Ivory linen co-ord, first-look energy", primary: "#f4e3c0", secondary: "#d7ae72", accent: "#f8ead6" },
  { id: "pool", label: "Pool Teal", category: "Pool", detail: "Daybed-ready poolside glow", primary: "#158a93", secondary: "#7bd1c7", accent: "#76d7d0" },
  { id: "date", label: "Date Night", category: "Date", detail: "Sleek black, evening tension", primary: "#201a1f", secondary: "#6f5a7d", accent: "#b8a7d9" },
  { id: "party", label: "Party Coral", category: "Party", detail: "Coral main-character entrance", primary: "#d94f43", secondary: "#ffae7a", accent: "#ff9e79" },
  { id: "challenge", label: "Challenge", category: "Challenge", detail: "Sporty, bright, ready to win", primary: "#e8b73a", secondary: "#e84d8a", accent: "#fff05a" },
  { id: "firepit", label: "Firepit White", category: "Ceremony", detail: "Elegant ceremony glow", primary: "#fffaf0", secondary: "#d0c1a7", accent: "#fffdfa" },
  { id: "finale", label: "Finale Gold", category: "Finale", detail: "Premium winner shine", primary: "#ffe48a", secondary: "#9c6b21", accent: "#ffe48a" },
];

export const ACCESSORIES: AccessoryOption[] = [
  { id: "sunglasses", label: "Sunglasses", slot: "Face", icon: "Glasses" },
  { id: "gold-hoops", label: "Gold hoops", slot: "Ears", icon: "Circle" },
  { id: "necklace", label: "Layered chains", slot: "Neck", icon: "Gem" },
  { id: "watch", label: "Watch", slot: "Wrist", icon: "Watch" },
  { id: "sun-hat", label: "Sun hat", slot: "Head", icon: "Crown" },
  { id: "anklet", label: "Anklet", slot: "Feet", icon: "Sparkle" },
  { id: "shades-tan", label: "Fresh tan", slot: "Skin", icon: "Sun" },
  { id: "rings", label: "Stacked rings", slot: "Hands", icon: "CircleDot" },
];

export const DEFAULT_LOOK: IslanderLook = {
  name: "",
  gender: "man",
  archetype: "heartthrob",
  skinTone: "tan",
  hairColor: "brown",
  outfit: "arrival",
  accessories: [],
  vibe: "sunny",
};

export function findOutfit(id: string): OutfitOption {
  return OUTFITS.find((o) => o.id === id) ?? OUTFITS[0];
}
export function findSkinTone(id: string): SwatchOption {
  return SKIN_TONES.find((s) => s.id === id) ?? SKIN_TONES[2];
}
export function findHairColor(id: string): SwatchOption {
  return HAIR_COLORS.find((s) => s.id === id) ?? HAIR_COLORS[1];
}
export function findVibe(id: string): SwatchOption {
  return VIBES.find((s) => s.id === id) ?? VIBES[0];
}
export function findArchetype(id: string): ArchetypeOption {
  return ARCHETYPES.find((a) => a.id === id) ?? ARCHETYPES[0];
}
export function findAccessory(id: string): AccessoryOption | undefined {
  return ACCESSORIES.find((a) => a.id === id);
}

// ---- Persistence -----------------------------------------------------------

const LOOK_PREFIX = "paradise.look.";
const DRAFT_KEY = "paradise.look.draft";

function sanitize(raw: unknown): IslanderLook {
  const look = { ...DEFAULT_LOOK, ...(raw as Partial<IslanderLook>) };
  // Coerce list-typed and enum-ish fields defensively so a malformed blob
  // never crashes the renderer.
  return {
    name: typeof look.name === "string" ? look.name.slice(0, 18) : "",
    gender: look.gender === "woman" ? "woman" : "man",
    archetype: (ARCHETYPES.some((a) => a.id === look.archetype) ? look.archetype : "heartthrob") as ArchetypeId,
    skinTone: findSkinTone(look.skinTone).id,
    hairColor: findHairColor(look.hairColor).id,
    outfit: findOutfit(look.outfit).id,
    accessories: Array.isArray(look.accessories)
      ? look.accessories.filter((id) => ACCESSORIES.some((a) => a.id === id)).slice(0, 8)
      : [],
    vibe: findVibe(look.vibe).id,
  };
}

export function saveLook(sessionId: string, look: IslanderLook): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(LOOK_PREFIX + sessionId, JSON.stringify(look));
}

export function loadLook(sessionId: string): IslanderLook | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(LOOK_PREFIX + sessionId);
  if (!raw) return null;
  try {
    return sanitize(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function saveDraftLook(look: IslanderLook): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(DRAFT_KEY, JSON.stringify(look));
}

export function loadDraftLook(): IslanderLook {
  if (typeof window === "undefined") return DEFAULT_LOOK;
  const raw = window.localStorage.getItem(DRAFT_KEY);
  if (!raw) return DEFAULT_LOOK;
  try {
    return sanitize(JSON.parse(raw));
  } catch {
    return DEFAULT_LOOK;
  }
}

/** Bind the in-progress draft to a freshly created session id. */
export function commitDraftToSession(sessionId: string, look: IslanderLook): void {
  saveLook(sessionId, look);
  saveDraftLook(look);
}
