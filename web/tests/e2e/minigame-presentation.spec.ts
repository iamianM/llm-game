import { expect, test } from "@playwright/test";

import { MINIGAME_BOARD_KINDS } from "../../components/minigame/MinigameBoard";
import { presentMinigame } from "../../lib/minigame/presentation";
import type { MinigameBoardView, MinigameKind, MinigameView } from "../../lib/minigame/types";
import type { AvailableAction } from "../../lib/types";

const BOARDS = {
  compatibility_quiz: {
    kind: "compatibility_quiz",
    latest_answer: {
      round_index: 0,
      chosen_label: "Sunrise",
      correct_label: "Sunrise",
      is_correct: true,
      points: 3,
      reaction_line: "You know each other.",
    },
  },
  heart_rate: {
    kind: "heart_rate",
    readings: [{ performer_id: "player", observer_id: "liam", bpm: 117, chemistry: 72 }],
  },
  couples_quiz: {
    kind: "couples_quiz",
    player_answer: "Terrace",
    partner_answer: "Terrace",
    aligned: true,
  },
  lie_detector: {
    kind: "lie_detector",
    subject_id: "chloe",
    verdict: "lie_caught",
    needle_percent: 23,
  },
  kiss_wed_pass: {
    kind: "kiss_wed_pass",
    allocations: [
      { role: "kiss", subject_id: "chloe" },
      { role: "wed", subject_id: "liam" },
      { role: "pass", subject_id: "maya" },
    ],
  },
  final_couples: {
    kind: "final_couples",
    facets: [
      { facet: "chemistry", score: 4 },
      { facet: "trust", score: 3 },
    ],
    final_tally: 7,
  },
} satisfies Record<MinigameKind, MinigameBoardView>;

test("the renderer registry is exhaustive for all six minigames", () => {
  expect(MINIGAME_BOARD_KINDS).toEqual(Object.keys(BOARDS));
});

test("available actions are the sole active-round choice authority", () => {
  const view = roundView(BOARDS.heart_rate);
  const result = presentMinigame(view, [
    action("challenge_response", "Hold Liam's gaze"),
    action("ambient", "Wait by the pool"),
  ]);

  expect(result.question).toBe("Whose pulse jumps?");
  expect(result.narration).toBe("The monitor settles.");
  expect(result.choices.map((choice) => choice.label)).toEqual(["Hold Liam's gaze"]);
});

test("active rounds fail closed without a legal challenge response", () => {
  expect(() => presentMinigame(roundView(BOARDS.couples_quiz), [action("ambient", "Wait")])).toThrow(
    "no challenge_response actions",
  );
});

test("a board cannot cross the discriminated minigame seam", () => {
  const view = { ...roundView(BOARDS.heart_rate), kind: "couples_quiz" } as MinigameView;
  expect(() => presentMinigame(view, [action("challenge_response", "Answer")])).toThrow(
    "does not match",
  );
});

function roundView(board: MinigameBoardView): MinigameView {
  return {
    status: "round",
    kind: board.kind,
    round_index: 1,
    round_count: 3,
    narration: "The monitor settles.",
    question: "Whose pulse jumps?",
    target_id: "liam",
    answered_rounds: [],
    board,
  };
}

function action(kind: string, label: string): AvailableAction {
  return {
    kind,
    label,
    target_id: "liam",
    intent_id: null,
    option_index: null,
    audience_hint: "",
    risk: null,
    stat_used: null,
  };
}
