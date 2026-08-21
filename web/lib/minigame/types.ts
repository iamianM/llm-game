import type { components } from "../openapi-types";

export type MinigameKind = components["schemas"]["MinigameKind"];
export type AnsweredMinigameRoundView = components["schemas"]["AnsweredMinigameRoundView"];
export type CompatibilityQuizBoardView = components["schemas"]["CompatibilityQuizBoardView"];
export type CouplesQuizBoardView = components["schemas"]["CouplesQuizBoardView"];
export type PulseReadingView = components["schemas"]["PulseReadingView"];
export type PulseRaceBoardView = components["schemas"]["PulseRaceBoardView"];
export type LieDetectorBoardView = components["schemas"]["LieDetectorBoardView"];
export type AllocationView = components["schemas"]["AllocationView"];
export type KissWedPassBoardView = components["schemas"]["KissWedPassBoardView"];
export type FacetScoreView = components["schemas"]["FacetScoreView"];
export type FinalCouplesBoardView = components["schemas"]["FinalCouplesBoardView"];
export type MinigameBoardView =
  | CompatibilityQuizBoardView
  | CouplesQuizBoardView
  | PulseRaceBoardView
  | LieDetectorBoardView
  | KissWedPassBoardView
  | FinalCouplesBoardView;
export type MinigameRoundView = components["schemas"]["MinigameRoundView"];
export type MinigameWrapView = components["schemas"]["MinigameWrapView"];
export type MinigameView = MinigameRoundView | MinigameWrapView;
