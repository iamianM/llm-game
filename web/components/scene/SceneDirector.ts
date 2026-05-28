import type { AvailableAction, SessionState, TurnResponse } from "../../lib/types";
import type { SceneBeat } from "../../lib/scene/types";
import { paginate } from "../../lib/scene/pagination";

export function planScene(
  prev: SessionState | null,
  next: SessionState,
  lastTurn: TurnResponse | null,
  availableActions: AvailableAction[],
): SceneBeat[] {
  void prev;
  const beats: SceneBeat[] = [];
  const activeSpeaker = lastTurn?.exchange?.speaker_id ?? next.active_conversation_target_id;
  if (next.pending_challenge) {
    beats.push({ kind: "camera", shot: "minigame_board", focusIds: activeSpeaker ? [activeSpeaker] : [], durationMs: 180 });
    if (String(next.pending_challenge.kind ?? "") === "heart_rate") {
      const firstNpc = next.islanders.find((islander) => !islander.eliminated);
      if (firstNpc) beats.push({ kind: "reaction", reactorId: firstNpc.id, pose: "exiting", durationMs: 900 });
    }
  } else if (activeSpeaker) {
    beats.push({ kind: "camera", shot: "two_shot", focusIds: [activeSpeaker], durationMs: 180 });
  } else if (lastTurn?.event_narration?.prose) {
    beats.push({ kind: "camera", shot: "narrator_full", focusIds: [], durationMs: 180 });
  } else {
    beats.push({ kind: "camera", shot: "wide_group", focusIds: [], durationMs: 120 });
  }

  const narration = prose(lastTurn?.event_narration);
  if (narration) {
    for (const page of paginate(narration)) beats.push({ kind: "narrator", text: page });
  }

  if (lastTurn?.exchange?.player_dialogue) {
    for (const page of paginate(lastTurn.exchange.player_dialogue)) {
      beats.push({ kind: "speech", speakerId: next.player.id, text: page, pose: "talking" });
    }
  }
  if (lastTurn?.exchange?.npc_dialogue) {
    for (const page of paginate(lastTurn.exchange.npc_dialogue)) {
      beats.push({ kind: "speech", speakerId: lastTurn.exchange.speaker_id, text: page, pose: "talking" });
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

  if (availableActions.length > 0) {
    beats.push({ kind: "choice_fan", spec: { actions: availableActions } });
  }
  return beats;
}

function prose(value: Record<string, unknown> | null | undefined): string | null {
  return typeof value?.prose === "string" && value.prose.trim() ? value.prose : null;
}
