import { greetingFor, nextIntroTarget } from "../../lib/intros";
import { paginate } from "../../lib/scene/pagination";
import {
  PLAYER_ANCHOR,
  PLAYER_ANCHOR_COMPACT,
  npcPositions,
} from "../../lib/scene/positions";
import type {
  ActionLanes,
  MinigamePresentationPort,
  PresentationTransition,
  SceneCastMember,
  SceneFeature,
  SceneFrame,
  ScenePlan,
  SceneSegment,
} from "../../lib/scene/presentation";
import type { CharacterPose, SceneBeat } from "../../lib/scene/types";
import type { AvailableAction, SessionState, TurnResponse } from "../../lib/types";

const PER_CHARACTER_KINDS = new Set(["start_conversation", "introduce_to"]);
const MOVE_KINDS = new Set(["move"]);
const MAX_STAGED_NPCS = 7;
const FEATURE_EVENT_KINDS = new Set([
  "pairing",
  "partner_stolen",
  "elimination",
  "pair_proposal",
  "npc_proposal_incoming",
  "npc_proposal_response",
  "private_suite",
  "flush_of_hearts_arrival",
  "flush_of_hearts_decision",
  "flush_of_hearts_return_reveal",
  "final_vote",
]);

export const NO_MINIGAME_PRESENTATION: MinigamePresentationPort<never> = {
  plan: () => null,
};

export function planScene<TSlot>(
  transition: PresentationTransition,
  minigamePresentation: MinigamePresentationPort<TSlot>,
): ScenePlan<TSlot> {
  const state = stateForTransition(transition);
  const actions = transitionActions(transition);
  const minigame = minigamePresentation.plan(transition);
  const actionLanes = routeActions(state, actions, minigame !== null);
  const features = planFeatures(transition);
  const scene = planGeneralSegment<TSlot>(
    transition,
    actionLanes,
    minigame !== null,
    features.length > 0,
  );
  const segments = compactSegments(scene, minigame);
  const beats = segments.flatMap((segment) => segment.beats);

  return {
    id: transitionId(transition),
    locationId: state.phase === "intros" ? "flame_deck" : state.location_id,
    segments,
    frames: planFrames(state, beats, actionLanes),
    actionLanes,
    features,
  };
}

export function stateForTransition(transition: PresentationTransition): SessionState {
  return transition.kind === "resolved" ? transition.response.state : transition.state;
}

function transitionActions(transition: PresentationTransition): readonly AvailableAction[] {
  return transition.kind === "resolved" ? transition.response.available_actions : transition.actions;
}

function transitionId(transition: PresentationTransition): string {
  if (transition.kind === "baseline") {
    return `${transition.state.session_id}:baseline:${transition.state.turn_index}`;
  }
  return `${transition.previous.session_id}:turn:${transition.previous.turn_index}`;
}

function compactSegments<TSlot>(
  scene: SceneSegment<TSlot>,
  minigame: SceneSegment<TSlot> | null,
): SceneSegment<TSlot>[] {
  if (!minigame) return [scene];
  if (scene.beats.length === 0) return [minigame];
  return [scene, minigame];
}

function routeActions(
  state: SessionState,
  actions: readonly AvailableAction[],
  minigameActive: boolean,
): ActionLanes {
  const useLanes =
    !minigameActive &&
    state.phase !== "intros" &&
    state.active_conversation_target_id === null;
  const character: AvailableAction[] = [];
  const move: AvailableAction[] = [];
  const fan: AvailableAction[] = [];

  for (const action of actions) {
    if (useLanes && PER_CHARACTER_KINDS.has(action.kind) && action.target_id) {
      character.push(action);
    } else if (useLanes && MOVE_KINDS.has(action.kind)) {
      move.push(action);
    } else {
      fan.push(action);
    }
  }

  const lanes: ActionLanes = { character, move, fan };
  assertExactActionPartition(actions, lanes);
  return lanes;
}

function assertExactActionPartition(actions: readonly AvailableAction[], lanes: ActionLanes): void {
  const routed = [...lanes.character, ...lanes.move, ...lanes.fan];
  if (routed.length !== actions.length) {
    throw new Error(`Scene action routing changed action count: ${actions.length} in, ${routed.length} out.`);
  }
  const remaining = [...routed];
  for (const action of actions) {
    const index = remaining.indexOf(action);
    if (index === -1) throw new Error(`Scene action routing dropped action: ${action.kind}.`);
    remaining.splice(index, 1);
  }
  if (remaining.length > 0) throw new Error("Scene action routing duplicated an action.");
}

function planGeneralSegment<TSlot>(
  transition: PresentationTransition,
  actionLanes: ActionLanes,
  minigameActive: boolean,
  hasFeatures: boolean,
): SceneSegment<TSlot> {
  const state = stateForTransition(transition);
  let beats: SceneBeat[];

  if (transition.kind === "pending") {
    beats = planPendingBeats(transition);
  } else if (state.phase === "intros") {
    beats = planIntroBeats(
      state,
      transition.kind === "resolved" ? transition.response : null,
      actionLanes.fan,
    );
  } else {
    beats = planResolvedBeats(
      state,
      transition.kind === "resolved" ? transition.response : null,
      actionLanes.fan,
      minigameActive,
      hasFeatures,
    );
  }

  return {
    id: `${transitionId(transition)}:scene`,
    beats,
    slot: null,
  };
}

function planPendingBeats(transition: Extract<PresentationTransition, { kind: "pending" }>): SceneBeat[] {
  const targetId = transition.stream.speakerId ?? transition.selectedAction.target_id;
  const beats: SceneBeat[] = [
    {
      kind: "camera",
      shot: targetId ? "two_shot" : "wide_group",
      focusIds: targetId ? [targetId] : [],
      durationMs: 80,
    },
  ];
  if (transition.stream.text && targetId) {
    beats.push({
      kind: "speech",
      speakerId: targetId,
      text: transition.stream.text,
      pose: "talking",
    });
  }
  return beats;
}

function planResolvedBeats(
  state: SessionState,
  turn: TurnResponse | null,
  fanActions: readonly AvailableAction[],
  minigameActive: boolean,
  hasFeatures: boolean,
): SceneBeat[] {
  const beats: SceneBeat[] = [];
  const exchange = turn?.exchange;
  const focusId = exchange?.speaker_id ?? state.active_conversation_target_id;
  beats.push({
    kind: "camera",
    shot: focusId ? "two_shot" : turn && prose(turn.event_narration) ? "narrator_full" : "wide_group",
    focusIds: focusId ? [focusId] : [],
    durationMs: focusId ? 160 : 120,
  });

  if (exchange?.player_dialogue) {
    for (const page of paginate(exchange.player_dialogue)) {
      beats.push({ kind: "speech", speakerId: state.player.id, text: page, pose: "talking" });
    }
  }
  if (exchange?.npc_dialogue) {
    for (const page of paginate(exchange.npc_dialogue)) {
      beats.push({ kind: "speech", speakerId: exchange.speaker_id, text: page, pose: "talking" });
    }
  }

  const shiftLine = turn?.connection_shift?.trim();
  if (shiftLine) {
    beats.push({
      kind: "connection_shift",
      subjectId: exchange?.speaker_id ?? focusId ?? state.player.id,
      text: shiftLine,
      durationMs: 1500,
    });
  }
  if (typeof turn?.audience_delta === "number" && turn.audience_delta !== 0) {
    beats.push({
      kind: "delta_pop",
      subjectId: state.player.id,
      deltaKind: "audience",
      amount: turn.audience_delta,
      durationMs: 900,
    });
  }

  const narration = !minigameActive && !hasFeatures ? prose(turn?.event_narration) : null;
  if (narration) {
    for (const page of paginate(narration)) beats.push({ kind: "narrator", text: page });
  }

  if (!minigameActive && fanActions.length > 0) {
    beats.push({ kind: "choice_fan", spec: { actions: [...fanActions] } });
  }
  return beats;
}

function planIntroBeats(
  state: SessionState,
  turn: TurnResponse | null,
  fanActions: readonly AvailableAction[],
): SceneBeat[] {
  const beats: SceneBeat[] = [];
  const exchange = turn?.exchange;
  const justFinished = exchange?.speaker_id ?? null;
  const nextTarget = nextIntroTarget(state.heartbreakers, [...fanActions], state.player.id);

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
    beats.push({ kind: "camera", shot: "wide_group", focusIds: [], durationMs: 120 });
    if (fanActions.length > 0) {
      beats.push({ kind: "choice_fan", spec: { actions: [...fanActions] } });
    }
    return beats;
  }

  beats.push({ kind: "camera", shot: "two_shot", focusIds: [nextTarget.id], durationMs: 160 });
  const dynamicGreeting = state.intros_greetings?.[nextTarget.id];
  beats.push({
    kind: "speech",
    speakerId: nextTarget.id,
    text: dynamicGreeting?.trim() || greetingFor(nextTarget),
    pose: "talking",
  });
  const introChoices = fanActions.filter(
    (action) => action.kind === "introduce_to" && action.target_id === nextTarget.id,
  );
  if (introChoices.length > 0) {
    beats.push({ kind: "choice_fan", spec: { actions: [...introChoices] } });
  }
  return beats;
}

function planFeatures(transition: PresentationTransition): SceneFeature[] {
  if (transition.kind !== "resolved") return [];
  const features: SceneFeature[] = [];
  transition.response.ceremony_events.forEach((event, index) => {
    if (!FEATURE_EVENT_KINDS.has(String(event.kind ?? ""))) return;
    features.push({
      id: `${transition.response.state_hash}:ceremony:${index}`,
      kind: "ceremony",
      event,
    });
  });

  const previousCount = transition.previous.daily_recaps.length;
  transition.response.state.daily_recaps.slice(previousCount).forEach((recap, index) => {
    features.push({
      id: `${transition.response.state_hash}:recap:${previousCount + index}`,
      kind: "recap",
      recap,
    });
  });
  return features;
}

function prose(value: Record<string, unknown> | null | undefined): string | null {
  return typeof value?.prose === "string" && value.prose.trim() ? value.prose : null;
}

function planFrames(
  state: SessionState,
  beats: readonly SceneBeat[],
  actionLanes: ActionLanes,
): SceneFrame[] {
  let cameraFocus: string | null = state.active_conversation_target_id;
  return beats.map((beat) => {
    if (beat.kind === "camera") cameraFocus = beat.focusIds[0] ?? null;
    const focusedId = focusForBeat(beat, cameraFocus, state);
    return frameFor(state, focusedId, poseForBeat(beat), beat.kind === "choice_fan");
  });
}

function focusForBeat(beat: SceneBeat, cameraFocus: string | null, state: SessionState): string | null {
  if (beat.kind === "speech" && beat.speakerId !== state.player.id) return beat.speakerId;
  if (beat.kind === "reaction") return beat.reactorId;
  if (beat.kind === "connection_shift" || beat.kind === "delta_pop") return beat.subjectId;
  return cameraFocus;
}

function poseForBeat(beat: SceneBeat): CharacterPose {
  if (beat.kind === "speech") return beat.pose ?? "talking";
  if (beat.kind === "reaction") return beat.pose;
  return "listening";
}

function frameFor(
  state: SessionState,
  focusedId: string | null,
  focusedPose: CharacterPose,
  choicesActive: boolean,
): SceneFrame {
  const visible = visibleNpcs(state, focusedId);
  const staged = stagedNpcs(visible, focusedId);
  const stagedIds = new Set(staged.map((npc) => npc.id));
  const groupPanelIds = visible.filter((npc) => !stagedIds.has(npc.id)).map((npc) => npc.id);
  const focusedIndex = focusedId ? staged.findIndex((npc) => npc.id === focusedId) : -1;
  const positions = npcPositions(staged.length, focusedIndex >= 0 ? focusedIndex : null);
  const cast: SceneCastMember[] = staged.map((npc, index) => ({
    id: npc.id,
    position: positions[index] ?? { x: 50, y: 56, scale: 0.7, dimmed: true },
    pose: npc.id === focusedId ? focusedPose : "listening",
    focused: npc.id === focusedId,
  }));
  cast.push({
    id: state.player.id,
    position: choicesActive ? PLAYER_ANCHOR_COMPACT : PLAYER_ANCHOR,
    pose: state.player.id === focusedId ? focusedPose : "listening",
    focused: state.player.id === focusedId,
  });
  return { cast, groupPanelIds };
}

function visibleNpcs(state: SessionState, focusedId: string | null) {
  const allHere = state.phase === "intros";
  return state.heartbreakers.filter((heartbreaker) => {
    if (heartbreaker.eliminated) return false;
    if (allHere || heartbreaker.id === focusedId) return true;
    return heartbreaker.location_id === state.location_id;
  });
}

function stagedNpcs<T extends { id: string }>(npcs: readonly T[], focusedId: string | null): T[] {
  if (npcs.length <= MAX_STAGED_NPCS) return [...npcs];
  const focused = focusedId ? npcs.find((npc) => npc.id === focusedId) : undefined;
  const staged = focused ? [focused] : [];
  for (const npc of npcs) {
    if (npc.id === focused?.id) continue;
    if (staged.length === MAX_STAGED_NPCS) break;
    staged.push(npc);
  }
  return staged;
}
