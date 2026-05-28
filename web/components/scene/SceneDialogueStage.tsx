"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { AvailableAction, SessionState, TurnResponse } from "../../lib/types";
import type { CharacterPose, Position, SceneBeat } from "../../lib/scene/types";
import { npcPositions, PLAYER_ANCHOR } from "../../lib/scene/positions";
import { type PendingChallengeView } from "../stage/ChallengeSpectacle";
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
      {showBanner(state.pending_challenge, actions) ? (
        <ChallengeBanner pending={state.pending_challenge as PendingChallengeView} />
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
  if (activeBeat?.kind === "speech" && activeBeat.speakerId !== state.player.id) return activeBeat.speakerId;
  if (activeBeat?.kind === "reaction") return activeBeat.reactorId;
  if (camera?.kind === "camera" && camera.focusIds[0]) return camera.focusIds[0];
  const pendingTarget = (state.pending_challenge as { target_id?: string | null } | null)?.target_id;
  return state.active_conversation_target_id ?? pendingTarget ?? null;
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

function showBanner(pending: SessionState["pending_challenge"], actions: AvailableAction[]) {
  if (!pending) return false;
  const finished = (pending as { finished?: boolean }).finished === true;
  if (!finished) return true;
  // Hide a wrapped challenge once the engine has moved on to a non-challenge
  // action set (e.g. recoupling picks) — the banner would otherwise mislead.
  return actions.some((action) => action.kind === "challenge_response");
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

const CHALLENGE_TITLES: Record<string, string> = {
  compatibility_quiz: "Compatibility Quiz",
  heart_rate: "Pulse Race",
  mr_and_mrs: "The Couples Quiz",
  lie_detector: "Lie Detector",
  snog_marry_pie: "Kiss · Wed · Pass",
  final_couples: "Final Couples",
};

function ChallengeBanner({ pending }: { pending: PendingChallengeView }) {
  const title = CHALLENGE_TITLES[pending.kind] ?? "Challenge";
  const total = pending.round_count ?? 1;
  const current = Math.min(total, (pending.round_index ?? 0) + 1);
  const pct = pending.finished ? 100 : Math.max(0, Math.min(100, ((pending.round_index ?? 0) / Math.max(1, total)) * 100));
  return (
    <div className="challenge-banner" data-testid="challenge-banner">
      <span className="challenge-banner-kicker">{title}</span>
      <span className="challenge-banner-round">
        {pending.finished ? "Wrap" : `Round ${current} / ${total}`}
      </span>
      <span className="challenge-banner-bar"><span style={{ width: `${pct}%` }} /></span>
      <style jsx>{`
        .challenge-banner {
          position: absolute;
          z-index: 11;
          top: 10px;
          left: 14px;
          display: grid;
          grid-template-columns: auto auto;
          column-gap: 12px;
          row-gap: 3px;
          align-items: baseline;
          padding: 7px 13px 8px;
          border-radius: var(--r-pill);
          background: rgba(20,16,12,.78);
          border: 1px solid rgba(217,167,58,.4);
          color: var(--card);
          box-shadow: var(--shadow-md), var(--inset-gold);
          font-family: var(--font-display);
          pointer-events: none;
          backdrop-filter: blur(8px);
        }
        .challenge-banner-kicker {
          font-size: 13px;
          font-weight: 650;
          letter-spacing: .04em;
        }
        .challenge-banner-round {
          font-size: 11px;
          letter-spacing: .14em;
          text-transform: uppercase;
          color: var(--gold-soft);
        }
        .challenge-banner-bar {
          grid-column: 1 / -1;
          width: 100%;
          height: 3px;
          border-radius: var(--r-pill);
          background: rgba(217,167,58,.15);
          overflow: hidden;
        }
        .challenge-banner-bar > span {
          display: block;
          height: 100%;
          background: linear-gradient(90deg, var(--accent), var(--gold));
          transition: width .35s ease;
        }
        @media (max-width: 520px) {
          .challenge-banner {
            top: 6px;
            left: 8px;
            padding: 5px 9px 6px;
          }
          .challenge-banner-kicker { font-size: 12px; }
          .challenge-banner-round { font-size: 10px; }
        }
      `}</style>
    </div>
  );
}
