export type BlackfenClassId = "fighter" | "rogue" | "mage";
export type BlackfenStatus = "active" | "victory" | "dead";

export type BlackfenPersistedSession = {
  persisted_schema_version: number;
  game_id: "blackfen_road";
  session_id: string;
  user_id: string | null;
  seed: number;
  rng_state: unknown[];
  game_state: Record<string, unknown>;
  mock_llm: boolean;
};

export type BlackfenLocation = {
  id: string;
  name: string;
  kind: string;
  image: string;
  description: string;
  exits: string[];
  npcs: string[];
};

export type BlackfenActor = {
  id: string;
  name: string;
  hp: number;
  max_hp: number;
  armor_class: number;
};

export type BlackfenNpc = {
  id: string;
  name: string;
  role: string;
  image: string;
  disposition: string;
};

export type BlackfenMonster = {
  id: string;
  name: string;
  image: string;
  hp: number;
};

export type BlackfenItem = {
  id: string;
  name: string;
  kind: string;
  image: string;
  description: string;
};

export type BlackfenState = {
  session_id: string;
  seed: number;
  turn_index: number;
  status: BlackfenStatus;
  state_hash: string;
  current_location: BlackfenLocation;
  known_locations: BlackfenLocation[];
  player: BlackfenActor;
  companion: BlackfenActor;
  companion_stance: string;
  npcs_here: BlackfenNpc[];
  monsters_here: BlackfenMonster[];
  inventory: BlackfenItem[];
  quest_flags: string[];
  journal: string[];
  last_narration: string | null;
};

export type BlackfenSessionResponse = {
  session_id: string;
  state: BlackfenState;
  suggestions: string[];
};

export type BlackfenNewEnvelope = {
  view: BlackfenSessionResponse;
  persisted: BlackfenPersistedSession;
};

export type BlackfenTurnResponse = {
  state: BlackfenState;
  narration: string;
  rolls: Record<string, unknown>[];
  suggestions: string[];
};

export type BlackfenTurnEnvelope = {
  view: BlackfenTurnResponse;
  persisted: BlackfenPersistedSession;
};
