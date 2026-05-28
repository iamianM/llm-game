import type { AvailableAction, SessionState, TurnResponse } from "../../lib/types";
import type { SceneBeat } from "../../lib/scene/types";
import { paginate } from "../../lib/scene/pagination";

type PendingChallenge = {
  kind?: string;
  finished?: boolean;
  stem?: string;
  round_index?: number;
  round_count?: number;
  target_id?: string | null;
  answered_rounds?: Array<{
    round_index: number;
    chosen_label: string | null;
    correct_label: string | null;
    is_correct: boolean;
    reaction_line: string | null;
  }>;
};

export function planScene(
  prev: SessionState | null,
  next: SessionState,
  lastTurn: TurnResponse | null,
  availableActions: AvailableAction[],
): SceneBeat[] {
  void prev;
  const beats: SceneBeat[] = [];
  const pending = next.pending_challenge as PendingChallenge | null;
  const exchange = lastTurn?.exchange;
  const exchangeSpeaker = exchange?.speaker_id ?? null;
  const challengeFocus = pending?.target_id ?? null;
  const focusSpeaker = exchangeSpeaker ?? challengeFocus ?? next.active_conversation_target_id;

  if (pending) {
    beats.push({
      kind: "camera",
      shot: "minigame_board",
      focusIds: challengeFocus ? [challengeFocus] : [],
      durationMs: 160,
    });
  } else if (focusSpeaker) {
    beats.push({ kind: "camera", shot: "two_shot", focusIds: [focusSpeaker], durationMs: 160 });
  } else if (lastTurn?.event_narration?.prose) {
    beats.push({ kind: "camera", shot: "narrator_full", focusIds: [], durationMs: 160 });
  } else {
    beats.push({ kind: "camera", shot: "wide_group", focusIds: [], durationMs: 120 });
  }

  const stillInChallengeForFeedback = availableActions.some((action) => action.kind === "challenge_response");
  const lastAnswered = stillInChallengeForFeedback ? lastAnsweredRound(pending) : null;
  if (lastAnswered) {
    beats.push({
      kind: "reaction",
      reactorId: challengeFocus ?? next.player.id,
      pose: lastAnswered.is_correct ? "reacting_good" : "reacting_bad",
      durationMs: 380,
    });
    const truth =
      !lastAnswered.is_correct && lastAnswered.correct_label
        ? `Truth: ${lastAnswered.correct_label}.`
        : null;
    const reaction = lastAnswered.reaction_line ?? null;
    const summary = [
      lastAnswered.is_correct ? "Nailed it." : "Off the mark.",
      lastAnswered.chosen_label ? `You said: ${lastAnswered.chosen_label}.` : null,
      truth,
      reaction,
    ]
      .filter(Boolean)
      .join(" ");
    if (summary) beats.push({ kind: "narrator", text: summary });
  }

  const narration = prose(lastTurn?.event_narration);
  if (narration) {
    for (const page of paginate(narration)) beats.push({ kind: "narrator", text: page });
  }

  if (exchange?.player_dialogue) {
    for (const page of paginate(exchange.player_dialogue)) {
      beats.push({ kind: "speech", speakerId: next.player.id, text: page, pose: "talking" });
    }
  }
  if (exchange?.npc_dialogue) {
    for (const page of paginate(exchange.npc_dialogue)) {
      beats.push({ kind: "speech", speakerId: exchange.speaker_id, text: page, pose: "talking" });
    }
  }
  if (typeof lastTurn?.audience_delta === "number" && lastTurn.audience_delta !== 0) {
    beats.push({
      kind: "delta_pop",
      subjectId: next.player.id,
      deltaKind: "audience",
      amount: lastTurn.audience_delta,
      durationMs: 900,
    });
  }

  if (pending && !pending.finished) {
    const stemText = quizStem(pending, next, challengeFocus);
    if (stemText) {
      const isContinuation = beats.some((b) => b.kind === "narrator" || b.kind === "speech");
      for (const page of paginate(stemText)) {
        if (isContinuation) {
          beats.push({ kind: "narrator", text: page });
        } else {
          beats.push({ kind: "narrator", text: page });
        }
      }
    }
  }

  if (pending?.finished) {
    const stillInChallenge = availableActions.some((action) => action.kind === "challenge_response");
    if (stillInChallenge) {
      const wrap = wrapNarration(pending);
      if (wrap) beats.push({ kind: "narrator", text: wrap });
    }
  }

  if (availableActions.length > 0) {
    beats.push({ kind: "choice_fan", spec: { actions: availableActions } });
  }
  return beats;
}

function prose(value: Record<string, unknown> | null | undefined): string | null {
  return typeof value?.prose === "string" && value.prose.trim() ? value.prose : null;
}

type AnsweredRound = NonNullable<PendingChallenge["answered_rounds"]>[number];

function lastAnsweredRound(pending: PendingChallenge | null): AnsweredRound | null {
  if (!pending?.answered_rounds?.length) return null;
  const sorted = [...pending.answered_rounds].sort((a, b) => a.round_index - b.round_index);
  const last = sorted[sorted.length - 1];
  const currentRound = pending.round_index ?? 0;
  // Only surface the previous round's result while a *new* round is pending,
  // or after the final round once the challenge is finished.
  if (pending.finished) return last;
  if (last.round_index >= currentRound) return null;
  return last;
}

function quizStem(pending: PendingChallenge, state: SessionState, focusId: string | null): string | null {
  const raw = typeof pending.stem === "string" ? pending.stem.trim() : "";
  if (!raw) return null;
  // Strip engine-side "Round N:" / "Q3:" / "Round 1 of 3 -" prefixes; the
  // banner already shows the round count, so a duplicate is just noise.
  const stripped = raw.replace(/^(?:round\s*\d+(?:\s*of\s*\d+)?|q\s*\d+)\s*[:\-—]\s*/i, "").trim();
  const stem = stripped || raw;
  const focus =
    focusId && state.islanders.find((i) => i.id === focusId)?.name
      ? state.islanders.find((i) => i.id === focusId)!.name
      : null;
  // Banner already says "ROUND N/M". Keep prefix focused on subject only.
  return focus ? `About ${focus}: ${stem}` : stem;
}

function wrapNarration(pending: PendingChallenge): string | null {
  const answered = pending.answered_rounds ?? [];
  if (!answered.length) return null;
  const right = answered.filter((r) => r.is_correct).length;
  return `Wrap: ${right} of ${answered.length} right. Tap to continue.`;
}
