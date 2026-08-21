import type { components } from "./openapi-types";

export type Gender = "man" | "woman";

export type DailyRecapView = components["schemas"]["DailyRecapView"];
export type MinigameRoundView = components["schemas"]["MinigameRoundView"];
export type MinigameWrapView = components["schemas"]["MinigameWrapView"];
export type MinigameView = MinigameRoundView | MinigameWrapView;

export type AvailableAction = {
  kind: string;
  label: string;
  target_id: string | null;
  intent_id: string | null;
  option_index: number | null;
  audience_hint: "+" | "-" | "";
  risk: string | null;
  stat_used: string | null;
  description?: string | null;
};

export type ApiMemory = {
  id: string;
  holder_id: string;
  subject_id: string;
  content: string;
  emotional_weight: number;
  source: string;
  tags: string[];
  formed_on_turn: number;
};

export type ApiKnownFact = {
  fact_key: string;
  label: string;
  value: string;
  source: string;
  source_npc_id: string | null;
  confidence: number;
  citation: string;
  group: "confirmed" | "heard" | "trivia";
};

// Four raw 0-100 bonds plus the engine-derived composite Connection: a single
// legible 0-100 score, its in-world tier word ("Just met" -> "Inseparable"),
// and the tier's ladder index (0-based) so the UI can fill/colour by intensity.
export type ApiRelationship = {
  affection: number;
  chemistry: number;
  trust: number;
  friendship: number;
  connection: number;
  connection_label: string;
  connection_tier: number;
};

// The four raw bonds, in the order they are shown as the Connection breakdown.
export const RELATIONSHIP_BONDS = ["chemistry", "affection", "trust", "friendship"] as const;
export type RelationshipBond = (typeof RELATIONSHIP_BONDS)[number];

export type HeartbreakerSummary = {
  id: string;
  name: string;
  gender: Gender;
  archetype: string;
  mood: string;
  location_id: string;
  location_label: string;
  eliminated: boolean;
  coupled: boolean;
  familiarity_with_player: number;
};

export type CoupleSummary = {
  partner_a_id: string;
  partner_b_id: string;
  partner_a_name: string;
  partner_b_name: string;
  strength: number;
  formed_on_day: number;
  formed_via: string;
  formed_via_label: string;
  rebound: boolean;
  is_player_couple: boolean;
};

export type SessionState = {
  session_id: string;
  schema_version: number;
  seed: number;
  day: number;
  phase: string;
  phase_label: string;
  turn_index: number;
  location_id: string;
  location_label: string;
  resort: string;
  resort_label: string;
  phase_clock: Record<string, unknown>;
  player: {
    id: string;
    name: string;
    gender: Gender;
    archetype_id: string;
    public_perception: number;
    stats: Record<string, number>;
    memories: ApiMemory[];
  };
  heartbreakers: HeartbreakerSummary[];
  couples: CoupleSummary[];
  audience: { public_perception: number; recent_delta: number | null; trend: string };
  pending_pair_proposal: Record<string, unknown> | null;
  pending_challenge: MinigameView | null;
  outcome: string | null;
  active_conversation_target_id: string | null;
  resort_snapshot: Record<string, string[]>;
  daily_recaps: DailyRecapView[];
  intros_greetings: Record<string, string>;
};

export type SessionResponse = {
  session_id: string;
  state: SessionState;
  available_actions: AvailableAction[];
};

export type TurnResponse = {
  state: SessionState;
  exchange: {
    speaker_id: string;
    speaker_name: string;
    player_dialogue: string;
    npc_dialogue: string;
    npc_tone: string;
    npc_mood_after: string;
  } | null;
  available_actions: AvailableAction[];
  ceremony_events: Array<Record<string, unknown>>;
  event_narration: Record<string, unknown> | null;
  audience_delta: number | null;
  audience_delta_reason: string | null;
  memories_formed: Array<Record<string, unknown>>;
  background_activity: Array<Record<string, unknown>>;
  // Short, in-world line for how this action shifted the player's bond with the
  // acted-on heartbreaker ("The spark with Chloe is electric."). Null when no bond
  // moved (idle moves, exits) — surfaced inline in-scene. Optional to match the
  // generated OpenAPI type (the field carries a Pydantic default).
  connection_shift?: string | null;
  state_hash: string;
};

export type CastDetail = {
  id: string;
  name: string;
  gender: Gender;
  archetype: string;
  mood: string;
  location: string;
  backstory: string;
  familiarity: number;
  relationship: ApiRelationship;
  ideal_match: Record<string, unknown | null>;
  known_facts: ApiKnownFact[];
  memories: ApiMemory[];
  coupled_with: string | null;
  eliminated: boolean;
};

export type PersistedSession = {
  schema_version: number;
  session_id: string;
  user_id: string | null;
  rng_state: unknown[];
  game_state: Record<string, unknown>;
  mock_llm: boolean;
};

export type NewSessionEnvelope = {
  view: SessionResponse;
  persisted: PersistedSession;
};

export type TurnResponseEnvelope = {
  view: TurnResponse;
  persisted: PersistedSession;
};

export type CheckpointSummary = {
  name: string;
  label: string;
  day: number;
  phase: string;
  source: "bundled" | "local";
};

export type CheckpointListResponse = {
  checkpoints: CheckpointSummary[];
};
