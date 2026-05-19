/**
 * Day-1 intros UI choreography.
 * The engine surfaces 4 dynamics × N non-partner Heartbreakers as flat options.
 * Game-feel wise we want: one NPC at a time, NPC greets first, player picks a
 * real conversational response. This module derives that flow from the engine's
 * action list without an engine change.
 */
import type { AvailableAction, IslanderSummary } from "./types";

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

/** Templated NPC greetings tailored loosely by archetype. */
const ARCHETYPE_GREETINGS: Record<string, string[]> = {
  sweetheart: [
    "Hi — I was hoping you'd come over. I'm {name}.",
    "Hey, you're new — come sit. I'm {name}.",
    "Oh, you. Come here. I'm {name}, by the way.",
  ],
  alpha: [
    "{name}. Pleasure. So, what's the read on you so far?",
    "Hey — {name}. Skip the small talk, what are you actually about?",
    "{name}. I've been waiting to see who you'd talk to first.",
  ],
  joker: [
    "Right, settle in. I'm {name}. We're absolutely doing this.",
    "Oh god, finally someone interesting. {name}. Hi.",
    "{name}. Be warned, I peaked socially around age twelve.",
  ],
  friend: [
    "Hi — I'm {name}. Was hoping we'd get to talk before things get wild.",
    "Hey. {name}. You look like you're about to be hugely outnumbered.",
    "{name}. Honestly relieved to be chatting with someone calm.",
  ],
};

const FALLBACK_GREETING = "Hey — I'm {name}. So… here we are.";

export function greetingFor(npc: IslanderSummary): string {
  const pool = ARCHETYPE_GREETINGS[npc.archetype] ?? null;
  if (!pool) return FALLBACK_GREETING.replace("{name}", npc.name);
  // Stable choice per session: hash on npc.id length + initial char
  const idx = (npc.id.length + npc.id.charCodeAt(0)) % pool.length;
  return pool[idx].replace("{name}", npc.name);
}

/** Return the next NPC the player should meet during intros. */
export function nextIntroTarget(
  islanders: IslanderSummary[],
  actions: AvailableAction[],
  playerId: string | undefined,
): IslanderSummary | null {
  // Sort all NPCs surfaced in the action list as INTRO targets, stable by name
  const targetsInActions = new Set(
    actions
      .filter((action) => action.kind === "introduce_to" && action.target_id)
      .map((action) => action.target_id as string),
  );
  const eligible = islanders.filter(
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

/** Pull the 4 intro actions for a specific NPC out of the flat action list. */
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
