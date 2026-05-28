/**
 * Maps engine intent_ids → high-level conversational categories used by the
 * tree-expand CharacterMenu and the in-conversation choice chips.
 *
 * The engine is the source of truth for what's *legal* (unlock thresholds,
 * tone gating, gossip eligibility). This file is the source of truth for
 * how the UI groups whatever the engine surfaced.
 */

export type IntentCategory = "friendly" | "flirty" | "deep" | "banter";

/**
 * Display copy for the category header + locked hint.
 */
export const CATEGORY_LABEL: Record<IntentCategory, string> = {
  friendly: "Be friendly with",
  flirty: "Flirt with",
  deep: "Get deep with",
  banter: "Banter with",
};

export const CATEGORY_SHORT: Record<IntentCategory, string> = {
  friendly: "Friendly",
  flirty: "Flirty",
  deep: "Deep",
  banter: "Banter",
};

/**
 * Affection threshold below which the category is dimmed and shows a hint
 * instead of expanding. Friendly + Banter are always available; Flirty
 * opens at 20; Deep at 40. Values mirror data/balance/intents.yaml.
 */
export const CATEGORY_UNLOCK_AFFECTION: Record<IntentCategory, number> = {
  friendly: 0,
  banter: 0,
  flirty: 20,
  deep: 40,
};

/**
 * One-line hint shown beneath a dimmed category button while it's locked.
 */
export const CATEGORY_LOCK_HINT: Record<IntentCategory, string> = {
  friendly: "",
  banter: "",
  flirty: "Get to know them a little first.",
  deep: "Build real trust first.",
};

/**
 * Mapping from any known intent_id → its category. Unknown intent_ids
 * default to `banter` (catch-all for follow-up templates that don't have
 * an obvious bucket).
 */
const INTENT_CATEGORY: Record<string, IntentCategory> = {
  // Intros (Day 1)
  intro_friendly: "friendly",
  intro_flirty: "flirty",
  intro_deep: "deep",
  intro_banter: "banter",
  // Free-time conversation start intents (data/balance/intents.yaml)
  friendly_ask_feelings: "friendly",
  friendly_chat_villa: "friendly",
  friendly_compliment_personality: "friendly",
  flirty_compliment_looks: "flirty",
  flirty_playful_teasing: "flirty",
  flirty_intimate_eye_contact: "flirty",
  deep_ask_life: "deep",
  deep_share_feelings: "deep",
  deep_discuss_connection: "deep",
  // In-conversation follow-ups (src/game/engine/option_defaults.py)
  honest_vulnerable: "deep",
  go_deeper: "deep",
  escalate_flirt: "flirty",
  joke_back: "banter",
  deflect_with_humor: "banter",
  defend_self: "banter",
  change_subject: "banter",
  walk_away: "banter",
  ask_about_topic: "friendly",
  apologize: "friendly",
  supportive_listen: "friendly",
  supportive_validate: "friendly",
  end_softly: "friendly",
};

export function categoryFor(intentId: string | null | undefined): IntentCategory {
  if (!intentId) return "banter";
  // Gossip and pull intents come through as prefixed strings — bucket
  // them under "banter" so they still appear somewhere.
  if (intentId.startsWith("share_gossip:") || intentId.startsWith("ask_gossip:")) {
    return "banter";
  }
  return INTENT_CATEGORY[intentId] ?? "banter";
}

/**
 * Intent IDs that exit the conversation entirely. UI surfaces these as a
 * sticky "leave" affordance rather than inside the category tree.
 */
export const EXIT_INTENTS: ReadonlySet<string> = new Set(["walk_away", "end_softly"]);

export const ORDERED_CATEGORIES: ReadonlyArray<IntentCategory> = ["friendly", "flirty", "deep", "banter"];
