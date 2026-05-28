"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { AvailableAction, SessionState, TurnResponse } from "../../lib/types";
import type { CharacterPose, Position, SceneBeat } from "../../lib/scene/types";
import { npcPositions, PLAYER_ANCHOR } from "../../lib/scene/positions";
import { ChallengeSpectacle, type PendingChallengeView } from "../stage/ChallengeSpectacle";
import { CharacterLayer } from "./CharacterLayer";
import { ChoiceFan } from "./ChoiceFan";
import { NarratorBubble } from "./NarratorBubble";
import { planScene } from "./SceneDirector";
import { SceneLayer } from "./SceneLayer";
import { SpeechBubble } from "./SpeechBubble";

type Props = {
  state: SessionState;
  actions: AvailableAction[];
  lastTurn: TurnResponse | null;
  locked: boolean;
  pendingActionLabel: string | null;
  streamText: string;
  streamSpeaker: string;
  onChoose: (action: AvailableAction) => void;
  onAdvance?: () => void;
};

export function SceneDialogueStage({
  state,
  actions,
  lastTurn,
  locked,
  pendingActionLabel,
  streamText,
  streamSpeaker,
  onChoose,
  onAdvance,
}: Props) {
  const plannedBeats = useMemo(
    () => locked
      ? pendingBeats(state, pendingActionLabel, streamText, streamSpeaker)
      : planScene(null, state, lastTurn, actions),
    [actions, lastTurn, locked, pendingActionLabel, state, streamSpeaker, streamText],
  );
  const [beatIndex, setBeatIndex] = useState(0);
  const sceneKey = `${state.turn_index}:${state.phase}:${lastTurn?.state_hash ?? "start"}:${locked ? "locked" : "ready"}:${actions.length}`;

  useEffect(() => setBeatIndex(0), [sceneKey]);

  const activeBeat = plannedBeats[Math.min(beatIndex, Math.max(0, plannedBeats.length - 1))];
  const currentCamera = cameraFor(plannedBeats, beatIndex);
  const focusedId = focusFor(activeBeat, currentCamera, state);
  const speakerPose = poseFor(activeBeat);
  const positionById = useMemo(() => spritePositions(state, focusedId), [focusedId, state]);
  const advance = useCallback(() => {
    if (!activeBeat || activeBeat.kind === "choice_fan") return;
    const remaining = plannedBeats.slice(beatIndex + 1);
    const moreDialogue = remaining.some((beat) => beat.kind === "speech" || beat.kind === "narrator");
    if (!moreDialogue) onAdvance?.();
    setBeatIndex((index) => Math.min(index + 1, plannedBeats.length - 1));
  }, [activeBeat, beatIndex, onAdvance, plannedBeats]);

  useEffect(() => {
    if (!activeBeat) return;
    if (activeBeat.kind !== "camera" && activeBeat.kind !== "reaction" && activeBeat.kind !== "delta_pop") return;
    const timeout = window.setTimeout(advance, activeBeat.durationMs);
    return () => window.clearTimeout(timeout);
  }, [activeBeat, advance]);

  return (
    <SceneLayer location={state.location_id} onTap={advance}>
      <CharacterLayer state={state} focusedId={focusedId} speakerPose={speakerPose} />
      {state.pending_challenge ? (
        <div className="minigame-slot" data-testid="scene-minigame-board">
          <ChallengeSpectacle state={state} pendingChallenge={state.pending_challenge as PendingChallengeView} />
        </div>
      ) : null}
      {activeBeat?.kind === "narrator" ? (
        <NarratorBubble text={activeBeat.text} canAdvance={hasLaterBeat(plannedBeats, beatIndex)} />
      ) : null}
      {activeBeat?.kind === "speech" ? (
        <SpeechBubble
          anchorId={activeBeat.speakerId}
          role={activeBeat.speakerId === state.player.id ? "player" : "npc"}
          speaker={speakerName(state, activeBeat.speakerId)}
          text={activeBeat.text}
          position={positionById.get(activeBeat.speakerId) ?? PLAYER_ANCHOR}
          canAdvance={hasLaterBeat(plannedBeats, beatIndex)}
        />
      ) : null}
      {activeBeat?.kind === "delta_pop" ? (
        <DeltaPop beat={activeBeat} position={positionById.get(activeBeat.subjectId) ?? PLAYER_ANCHOR} />
      ) : null}
      {activeBeat?.kind === "choice_fan" ? (
        <ChoiceFan actions={activeBeat.spec.actions} locked={locked} onChoose={onChoose} />
      ) : null}
      <style jsx>{`
        .minigame-slot {
          position: absolute;
          z-index: 4;
          left: 50%;
          top: 43%;
          width: min(960px, calc(100vw - 24px));
          transform: translate(-50%, -50%) scale(.86);
          pointer-events: none;
        }
        .minigame-slot :global(*) {
          pointer-events: none;
        }
        @media (max-width: 760px) {
          .minigame-slot {
            top: 38%;
            transform: translate(-50%, -50%) scale(.62);
          }
        }
      `}</style>
    </SceneLayer>
  );
}

function pendingBeats(state: SessionState, playerLine: string | null, streamText: string, streamSpeaker: string): SceneBeat[] {
  const activeSpeaker = state.active_conversation_target_id;
  const beats: SceneBeat[] = [
    { kind: "camera", shot: activeSpeaker ? "two_shot" : "wide_group", focusIds: activeSpeaker ? [activeSpeaker] : [], durationMs: 80 },
  ];
  if (playerLine) beats.push({ kind: "speech", speakerId: state.player.id, text: playerLine, pose: "talking" });
  beats.push({
    kind: "speech",
    speakerId: activeSpeaker ?? state.player.id,
    text: streamText || "Sunset Bay is reacting...",
    pose: "talking",
  });
  void streamSpeaker;
  return beats;
}

function cameraFor(beats: SceneBeat[], activeIndex: number) {
  for (let index = activeIndex; index >= 0; index -= 1) {
    const beat = beats[index];
    if (beat?.kind === "camera") return beat;
  }
  return null;
}

function focusFor(activeBeat: SceneBeat | undefined, camera: SceneBeat | null, state: SessionState): string | null {
  if (activeBeat?.kind === "speech") return activeBeat.speakerId;
  if (activeBeat?.kind === "reaction") return activeBeat.reactorId;
  if (camera?.kind === "camera" && camera.focusIds[0]) return camera.focusIds[0];
  return state.active_conversation_target_id;
}

function poseFor(activeBeat: SceneBeat | undefined): CharacterPose {
  if (activeBeat?.kind === "speech") return activeBeat.pose ?? "talking";
  if (activeBeat?.kind === "reaction") return activeBeat.pose;
  return "listening";
}

function spritePositions(state: SessionState, focusedId: string | null): Map<string, Position> {
  const map = new Map<string, Position>();
  const npcs = state.islanders.filter((islander) => !islander.eliminated);
  const focusedIndex = focusedId ? npcs.findIndex((npc) => npc.id === focusedId) : null;
  const positions = npcPositions(npcs.length, focusedIndex !== null && focusedIndex >= 0 ? focusedIndex : null);
  npcs.forEach((npc, index) => map.set(npc.id, positions[index] ?? { x: 50, y: 56, scale: 0.7 }));
  map.set(state.player.id, PLAYER_ANCHOR);
  return map;
}

function speakerName(state: SessionState, speakerId: string) {
  if (speakerId === state.player.id) return state.player.name || "You";
  return state.islanders.find((npc) => npc.id === speakerId)?.name ?? "The Producer";
}

function hasLaterBeat(beats: SceneBeat[], index: number) {
  return index < beats.length - 1;
}

function DeltaPop({ beat, position }: { beat: Extract<SceneBeat, { kind: "delta_pop" }>; position: Position }) {
  return (
    <div
      data-testid="delta-pop"
      className={`delta-pop ${beat.amount > 0 ? "is-good" : "is-bad"}`}
      style={{ left: `${position.x}%`, top: `${Math.max(8, position.y - 38)}%` }}
    >
      Pulse {beat.amount > 0 ? "+" : ""}{beat.amount}
      <style jsx>{`
        .delta-pop {
          position: absolute;
          z-index: 11;
          transform: translate(-50%, -50%);
          padding: 6px 12px;
          border-radius: var(--r-pill);
          font-size: 12px;
          font-weight: 800;
          letter-spacing: .08em;
          text-transform: uppercase;
          animation: delta-pop .9s ease-out both;
          box-shadow: var(--shadow-md);
        }
        .is-good {
          color: var(--good-soft);
          background: rgba(45,106,63,.82);
          border: 1px solid rgba(164,205,177,.55);
        }
        .is-bad {
          color: var(--bad-soft);
          background: rgba(193,75,58,.82);
          border: 1px solid rgba(247,226,221,.55);
        }
        @keyframes delta-pop {
          from { opacity: 0; transform: translate(-50%, -30%) scale(.92); }
          20% { opacity: 1; }
          to { opacity: 0; transform: translate(-50%, -90%) scale(1.03); }
        }
      `}</style>
    </div>
  );
}
