/**
 * Day-1 intros UI choreography.
 * The engine surfaces 4 dynamics × N non-partner Heartbreakers as flat options.
 * Game-feel wise we want: one NPC at a time, NPC greets first, player picks a
 * real conversational response. This module derives that flow from the engine's
 * action list without an engine change.
 */
import type { AvailableAction, HeartbreakerSummary } from "./types";

export const INTRO_DYNAMICS = ["intro_friendly", "intro_flirty", "intro_deep", "intro_banter"] as const;
export type IntroDynamic = (typeof INTRO_DYNAMICS)[number];

/** A response option the player can say, written as actual dialogue. */
export const INTRO_RESPONSES: Record<IntroDynamic, { label: string; line: string; tone: string }> = {
  intro_friendly: {
    label: "Friendly",
    line: "Honestly, hard not to vibe with you on day one.",
    tone: "warm, easy, low risk",
  },
  intro_flirty: {
    label: "Flirty",
    line: "Depends — you giving me anything to look at?",
    tone: "playful, suggestive",
  },
  intro_deep: {
    label: "Deep",
    line: "Bit overwhelmed if I'm honest. You feeling that too?",
    tone: "vulnerable, real",
  },
  intro_banter: {
    label: "Banter",
    line: "Trying not to embarrass myself yet. Give it ten minutes.",
    tone: "self-roast, charming",
  },
};

const RESPONSE_VARIANTS: Partial<Record<string, Partial<Record<IntroDynamic, string[]>>>> = {
  sweetheart: {
    intro_friendly: [
      "You make this feel less terrifying already.",
      "I was hoping you would be easy to talk to.",
      "Honestly, your energy is exactly what I needed first.",
    ],
    intro_deep: [
      "I am trying to stay present, but this is a lot. You too?",
      "You seem calm. Is that real, or are you hiding the panic better than me?",
      "I want this to feel honest from the start. How are you really doing?",
    ],
  },
  alpha: {
    intro_flirty: [
      "Confident opener. Dangerous. I might need to see if you can back it up.",
      "You do not waste time, do you? I respect that.",
      "That sounded like a challenge. I am listening.",
    ],
    intro_banter: [
      "Strong entrance. I give it eight out of ten until proven otherwise.",
      "You are intense in a fun way. Probably trouble, but fun.",
      "I was going to play it cool, then you went and made that difficult.",
    ],
  },
  joker: {
    intro_banter: [
      "Good, someone who understands this is all deeply unserious until it is not.",
      "If we embarrass ourselves, I vote we commit fully.",
      "You look like you might be my best chance at surviving the awkward bits.",
    ],
    intro_friendly: [
      "You are making this easier than expected, which is suspicious but welcome.",
      "I am choosing to trust the grin. Big decision, honestly.",
      "Okay, I like your timing already.",
    ],
  },
  friend: {
    intro_friendly: [
      "You feel like someone I could actually breathe around in here.",
      "I like this pace. No performance, just a real hello.",
      "You seem steady. That might be rare in here.",
    ],
    intro_deep: [
      "I am a bit overwhelmed, honestly. You seem like you might get that.",
      "This place is beautiful and a lot. I am trying to work out which matters more.",
      "I would rather start real than polished. How are you holding up?",
    ],
  },
};

export function responseFor(npc: HeartbreakerSummary, dynamic: IntroDynamic): string {
  const variants = RESPONSE_VARIANTS[npc.archetype]?.[dynamic];
  if (!variants?.length) return INTRO_RESPONSES[dynamic].line;
  return variants[fnv1a(`${npc.id}|${dynamic}`) % variants.length];
}

function fnv1a(input: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

/** Templated NPC greetings tailored loosely by archetype.
 * Each line MUST be self-introducing — the speaker is the NPC, the player
 * is being greeted. Lines like "Hey, {name}." are ambiguous (sounds like
 * the NPC is addressing the player by name) so we always anchor with "I'm".
 */
const ARCHETYPE_GREETINGS: Record<string, string[]> = {
  sweetheart: [
    "Hi — I was hoping you'd come over. I'm {name}.",
    "Hey, you're new — come sit. I'm {name}.",
    "Oh, you. Come here. I'm {name}, by the way.",
  ],
  alpha: [
    "I'm {name}. Pleasure. So, what's the read on you so far?",
    "Hey — I'm {name}. Skip the small talk, what are you actually about?",
    "I'm {name}. I've been waiting to see who you'd talk to first.",
  ],
  joker: [
    "Right, settle in. I'm {name}. We're absolutely doing this.",
    "Oh god, finally someone interesting. I'm {name}. Hi.",
    "I'm {name}. Be warned, I peaked socially around age twelve.",
  ],
  friend: [
    "Hi — I'm {name}. Was hoping we'd get to talk before things get wild.",
    "I'm {name}. You look like you're about to be hugely outnumbered. Solidarity.",
    "I'm {name}. Honestly relieved to be chatting with someone calm.",
  ],
};

const FALLBACK_GREETING = "Hey — I'm {name}. So… here we are.";

export function greetingFor(npc: HeartbreakerSummary): string {
  const pool = ARCHETYPE_GREETINGS[npc.archetype] ?? null;
  if (!pool) return FALLBACK_GREETING.replace("{name}", npc.name);
  // Stable choice per session: hash on npc.id length + initial char
  const idx = (npc.id.length + npc.id.charCodeAt(0)) % pool.length;
  return pool[idx].replace("{name}", npc.name);
}

/** Return the next NPC the player should meet during intros. */
export function nextIntroTarget(
  heartbreakers: HeartbreakerSummary[],
  actions: AvailableAction[],
  playerId: string | undefined,
): HeartbreakerSummary | null {
  // Sort all NPCs surfaced in the action list as INTRO targets, stable by name
  const targetsInActions = new Set(
    actions
      .filter((action) => action.kind === "introduce_to" && action.target_id)
      .map((action) => action.target_id as string),
  );
  const eligible = heartbreakers.filter(
    (npc) =>
      !npc.eliminated &&
      npc.id !== playerId &&
      targetsInActions.has(npc.id) &&
      npc.familiarity_with_player < 25,
  );
  if (!eligible.length) return null;
  // Order: lowest familiarity first, then stable by id
  eligible.sort((a, b) => {
    if (a.familiarity_with_player !== b.familiarity_with_player) {
      return a.familiarity_with_player - b.familiarity_with_player;
    }
    return a.id.localeCompare(b.id);
  });
  return eligible[0];
}

/** Extract the 4 intro actions for a specific NPC out of the flat action list. */
export function introActionsForTarget(
  actions: AvailableAction[],
  targetId: string,
): Partial<Record<IntroDynamic, AvailableAction>> {
  const map: Partial<Record<IntroDynamic, AvailableAction>> = {};
  for (const action of actions) {
    if (action.kind !== "introduce_to") continue;
    if (action.target_id !== targetId) continue;
    if (!action.intent_id) continue;
    if (INTRO_DYNAMICS.includes(action.intent_id as IntroDynamic)) {
      map[action.intent_id as IntroDynamic] = action;
    }
  }
  return map;
}
