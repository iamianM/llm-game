import type { AvailableAction, SessionState, TurnResponse } from "../../lib/types";
import type { SceneBeat } from "../../lib/scene/types";
import { paginate } from "../../lib/scene/pagination";
import { greetingFor, nextIntroTarget } from "../../lib/intros";

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
  if (next.phase === "intros") {
    return planIntroScene(next, lastTurn, availableActions);
  }
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
  // A felt "your bond just moved" cue, floated by the islander we just engaged.
  // Anchored to the exchange speaker (the person we steered toward); auto-advances.
  const shiftLine = lastTurn?.connection_shift?.trim();
  if (shiftLine) {
    const anchor = exchangeSpeaker ?? focusSpeaker ?? next.player.id;
    beats.push({ kind: "connection_shift", subjectId: anchor, text: shiftLine, durationMs: 1500 });
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

  // The challenge stem is read aloud as a narrator beat (the dramatic reveal,
  // keeping the host's scene-setting flavor) AND distilled to a concise question
  // that rides on the choice_fan — otherwise the question vanishes the moment the
  // answer options appear and the player is left choosing blind.
  let challengePrompt: string | null = null;
  if (pending && !pending.finished) {
    const raw = typeof pending.stem === "string" ? pending.stem.trim() : "";
    if (raw) {
      challengePrompt = challengeQuestion(raw);
      for (const page of paginate(cleanStem(raw))) beats.push({ kind: "narrator", text: page });
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
    beats.push({
      kind: "choice_fan",
      spec: challengePrompt ? { actions: availableActions, prompt: challengePrompt } : { actions: availableActions },
    });
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

// Drop the leading round label ("Round 3:", "Q2 —", "Round 2 of 3:") since the
// banner already shows "Round N / M", plus any redundant "about <name>:" lead-in
// (the Couples Quiz repeats the subject the question already names). The scene +
// question body is preserved — these stems are written as cohesive prompts.
function cleanStem(raw: string): string {
  const out = raw
    .replace(/^(?:round\s*\d+(?:\s*of\s*\d+)?|q\s*\d+)\s*[:\-—]\s*/i, "")
    .replace(/^about\s+[^:]+:\s*/i, "")
    .trim();
  const cleaned = out || raw.trim();
  // Stripping a label can leave a lowercase fragment ("partner's turn. ...");
  // re-capitalize so it reads as a proper sentence.
  return cleaned.replace(/^([a-z])/, (m) => m.toUpperCase());
}

// The concise question for the persistent prompt card. Challenges open with
// host flavor / mechanic explanation (the Lie Detector spends four sentences
// wiring up the needle before it ever asks anything) that belongs in the
// scrolling narrator beat, not pinned over the answer buttons. Distill the raw
// stem down to the actual ask:
//   1. Drop a "...Round one[ is about <name>]:" scene-setting intro (the compat
//      / couples quizzes mark the split explicitly).
//   2. Otherwise trim to the sentence that first poses a question, through the
//      end — so a trailing answer instruction ("(Pick what Chloe actually
//      said…)") survives while the preamble is dropped. A stem with no "?" is
//      an imperative prompt, so keep the cleaned stem as-is.
function challengeQuestion(raw: string): string {
  const afterIntro = raw.replace(/^[\s\S]*?\bround\s+one\b(?:\s+is\s+about\s+[^:]+)?:\s*/i, "");
  const base = afterIntro !== raw ? afterIntro : raw;
  return cleanStem(trimToQuestion(base));
}

// Return the substring starting at the sentence that first contains a "?", so
// scene-setting that precedes the ask is dropped but the question (and anything
// after it, e.g. a parenthetical instruction) is kept. No "?" → return as-is.
function trimToQuestion(text: string): string {
  const qIdx = text.indexOf("?");
  if (qIdx === -1) return text;
  const before = text.slice(0, qIdx);
  const boundary = Math.max(
    before.lastIndexOf(". "),
    before.lastIndexOf("! "),
    before.lastIndexOf("? "),
    before.lastIndexOf("\n"),
  );
  const start = boundary === -1 ? 0 : boundary + 1;
  return text.slice(start).trim();
}

function wrapNarration(pending: PendingChallenge): string | null {
  const answered = pending.answered_rounds ?? [];
  if (!answered.length) return null;
  const right = answered.filter((r) => r.is_correct).length;
  return `Wrap: ${right} of ${answered.length} right. Tap to continue.`;
}

/**
 * Day-1 intros: NPCs greet the player one at a time, in the firepit.
 * After each pick, the engine response is surfaced as a narrator beat then
 * we auto-cycle to the next target. Once everyone is met, the engine
 * transitions phase and the next planScene call covers what comes after.
 */
function planIntroScene(
  state: SessionState,
  lastTurn: TurnResponse | null,
  availableActions: AvailableAction[],
): SceneBeat[] {
  const beats: SceneBeat[] = [];
  const exchange = lastTurn?.exchange;
  const justFinished = exchange?.speaker_id ?? null;
  const introTargets = availableActions
    .filter((a) => a.kind === "introduce_to" && a.target_id)
    .map((a) => a.target_id as string);
  const nextTarget = nextIntroTarget(state.islanders, availableActions, state.player.id);

  // Show the just-finished exchange first (player line then NPC reply) so the
  // user can read the response before the camera swings to the next islander.
  // Keep the islander we're replying to spotlighted for the whole exchange —
  // including the player's own line — so they don't drop to the back row the
  // instant the player speaks and then snap forward again for their reply.
  if (justFinished && (exchange?.player_dialogue || exchange?.npc_dialogue)) {
    beats.push({ kind: "camera", shot: "two_shot", focusIds: [justFinished], durationMs: 140 });
  }
  if (exchange?.player_dialogue) {
    for (const page of paginate(exchange.player_dialogue)) {
      beats.push({ kind: "speech", speakerId: state.player.id, text: page, pose: "talking" });
    }
  }
  if (exchange?.npc_dialogue && justFinished) {
    for (const page of paginate(exchange.npc_dialogue)) {
      beats.push({ kind: "speech", speakerId: justFinished, text: page, pose: "talking" });
    }
  }

  if (!nextTarget) {
    if (introTargets.length === 0) {
      // No more intros available — the engine has moved on; let normal
      // planScene logic run by emitting a wide-group beat + choice fan.
      beats.push({ kind: "camera", shot: "wide_group", focusIds: [], durationMs: 120 });
      if (availableActions.length > 0) {
        beats.push({ kind: "choice_fan", spec: { actions: availableActions } });
      }
    }
    return beats;
  }

  // Frame the next islander, NPC greets first, then the player picks an intent.
  beats.push({ kind: "camera", shot: "two_shot", focusIds: [nextTarget.id], durationMs: 160 });
  // Prefer dynamically-generated greetings (live mode); fall back to per-archetype
  // templates so demo mode and pre-feature checkpoints still read cleanly.
  const dynamicGreeting = state.intros_greetings?.[nextTarget.id];
  const greeting = dynamicGreeting && dynamicGreeting.trim().length > 0
    ? dynamicGreeting
    : greetingFor(nextTarget);
  beats.push({ kind: "speech", speakerId: nextTarget.id, text: greeting, pose: "talking" });

  // Show the engine's intent-labeled choices ("Be friendly with X", etc.)
  // unchanged — no preview-line rewriting. The bubble shows the *intent dial*,
  // the engine's islander_voice writes the actual line on click.
  const introChoices = availableActions.filter(
    (a) => a.kind === "introduce_to" && a.target_id === nextTarget.id,
  );
  if (introChoices.length > 0) {
    beats.push({ kind: "choice_fan", spec: { actions: introChoices } });
  }
  return beats;
}
