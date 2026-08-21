/**
 * Module-local mirror of src/game/presentation/minigame.py.
 *
 * Controlled integration replaces these declarations with aliases to the
 * generated OpenAPI models once SessionState.pending_challenge adopts the
 * Pydantic projection.
 */

export type MinigameKind =
  | "compatibility_quiz"
  | "heart_rate"
  | "couples_quiz"
  | "lie_detector"
  | "kiss_wed_pass"
  | "final_couples";

export type AnsweredMinigameRoundView = {
  round_index: number;
  chosen_label: string | null;
  correct_label: string | null;
  is_correct: boolean;
  points: number;
  reaction_line: string | null;
};

export type CompatibilityQuizBoardView = {
  kind: "compatibility_quiz";
  latest_answer: AnsweredMinigameRoundView | null;
};

export type CouplesQuizBoardView = {
  kind: "couples_quiz";
  player_answer: string | null;
  partner_answer: string | null;
  aligned: boolean | null;
};

export type PulseReadingView = {
  performer_id: string;
  observer_id: string;
  bpm: number;
  chemistry: number;
};

export type PulseRaceBoardView = {
  kind: "heart_rate";
  readings: PulseReadingView[];
};

export type LieDetectorBoardView = {
  kind: "lie_detector";
  subject_id: string | null;
  verdict: "truth_told" | "truth_suspected" | "lie_caught" | "lie_believed" | null;
  needle_percent: number | null;
};

export type AllocationView = {
  role: "kiss" | "wed" | "pass";
  subject_id: string;
};

export type KissWedPassBoardView = {
  kind: "kiss_wed_pass";
  allocations: AllocationView[];
};

export type FacetScoreView = {
  facet: string;
  score: number;
};

export type FinalCouplesBoardView = {
  kind: "final_couples";
  facets: FacetScoreView[];
  final_tally: number | null;
};

export type MinigameBoardView =
  | CompatibilityQuizBoardView
  | CouplesQuizBoardView
  | PulseRaceBoardView
  | LieDetectorBoardView
  | KissWedPassBoardView
  | FinalCouplesBoardView;

type MinigameViewBase = {
  kind: MinigameKind;
  round_count: number;
  narration: string;
  answered_rounds: AnsweredMinigameRoundView[];
  board: MinigameBoardView;
};

export type MinigameRoundView = MinigameViewBase & {
  status: "round";
  round_index: number;
  question: string;
  target_id: string | null;
};

export type MinigameWrapView = MinigameViewBase & {
  status: "wrap";
  classification: "success" | "partial" | "failure";
  total_points: number;
  audience_delta: number;
};

export type MinigameView = MinigameRoundView | MinigameWrapView;
