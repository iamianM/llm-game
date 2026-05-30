import type { AvailableAction } from "../types";

export type CameraShot =
  | "wide_group"
  | "two_shot"
  | "speaker_focus"
  | "narrator_full"
  | "minigame_board"
  | "cutscene";

export type CharacterPose =
  | "idle"
  | "talking"
  | "listening"
  | "reacting_good"
  | "reacting_bad"
  | "exiting"
  | "off_stage";

export type Position = {
  x: number;
  y: number;
  scale: number;
  dimmed?: boolean;
  hidden?: boolean;
};

export type ChoiceFanSpec = {
  actions: AvailableAction[];
  // For round-based challenges (quizzes, lie detector, etc.) the question stem
  // is delivered as a dramatic narrator beat, then vanishes when the answer
  // options appear. Carrying it here lets the stage pin the question on-screen
  // as a persistent prompt card so the player can read it while choosing.
  prompt?: string;
};

export type SceneBeat =
  | { kind: "narrator"; text: string; sourceEventId?: string }
  | { kind: "speech"; speakerId: string; text: string; pose?: CharacterPose }
  | { kind: "reaction"; reactorId: string; pose: CharacterPose; durationMs: number }
  | { kind: "camera"; shot: CameraShot; focusIds: string[]; durationMs: number }
  | { kind: "choice_fan"; spec: ChoiceFanSpec }
  | { kind: "delta_pop"; subjectId: string; deltaKind: "audience" | "affection" | "loyalty"; amount: number; durationMs: number };
