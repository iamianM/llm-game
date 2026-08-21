import type { AvailableAction } from "../types";
import type { MinigameBoardView, MinigameKind, MinigameView } from "./types";

type MinigameMeta = {
  title: string;
  kicker: string;
};

const MINIGAME_META = {
  compatibility_quiz: { title: "Compatibility Quiz", kicker: "Know your couple" },
  heart_rate: { title: "Pulse Race", kicker: "Monitors live" },
  couples_quiz: { title: "The Couples Quiz", kicker: "Private answers, public stakes" },
  lie_detector: { title: "Lie Detector", kicker: "The result is in" },
  kiss_wed_pass: { title: "Kiss Wed Pass", kicker: "Three cards, no hiding" },
  final_couples: { title: "Final Couples Challenge", kicker: "The last public test" },
} satisfies Record<MinigameKind, MinigameMeta>;

export type MinigamePresentation = {
  id: string;
  title: string;
  kicker: string;
  status: "round" | "wrap";
  roundLabel: string;
  progressPercent: number;
  narration: string;
  question: string | null;
  board: MinigameBoardView;
  choices: readonly AvailableAction[];
};

/** Interpret one typed minigame view behind the scene presentation seam. */
export function presentMinigame(
  view: MinigameView,
  availableActions: readonly AvailableAction[],
): MinigamePresentation {
  if (view.board.kind !== view.kind) {
    throw new Error(`Minigame board kind ${view.board.kind} does not match ${view.kind}.`);
  }
  const meta = MINIGAME_META[view.kind];
  if (view.status === "round") {
    const choices = availableActions.filter((action) => action.kind === "challenge_response");
    if (choices.length === 0) {
      throw new Error(`Active ${view.kind} round has no challenge_response actions.`);
    }
    return {
      id: `${view.kind}:round:${view.round_index}`,
      title: meta.title,
      kicker: meta.kicker,
      status: view.status,
      roundLabel: `Round ${view.round_index + 1} / ${view.round_count}`,
      progressPercent: Math.round((view.round_index / view.round_count) * 100),
      narration: view.narration,
      question: view.question,
      board: view.board,
      choices,
    };
  }
  return {
    id: `${view.kind}:wrap`,
    title: meta.title,
    kicker: meta.kicker,
    status: view.status,
    roundLabel: "Wrap",
    progressPercent: 100,
    narration: view.narration,
    question: null,
    board: view.board,
    choices: [],
  };
}
