"use client";

import { ChevronLeft, Lock, MapPin, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { AvailableAction, SessionState, TurnResponse } from "../../lib/types";
import type { CharacterPose, Position, SceneBeat } from "../../lib/scene/types";
import { npcPositions, PLAYER_ANCHOR } from "../../lib/scene/positions";
import {
  CATEGORY_LABEL,
  CATEGORY_LOCK_HINT,
  CATEGORY_SHORT,
  ORDERED_CATEGORIES,
  categoryFor,
  type IntentCategory,
} from "../../lib/scene/intents";
import { type PendingChallengeView } from "../stage/ChallengeSpectacle";
import { CharacterLayer, visibleNpcs } from "./CharacterLayer";
import { ChoiceFan } from "./ChoiceFan";
import { NarratorBubble } from "./NarratorBubble";
import { planScene } from "./SceneDirector";
import { SceneLayer } from "./SceneLayer";
import { SpeechBubble } from "./SpeechBubble";

// Action kinds that target a specific character via target_id — these are
// reached by tapping the character, not from the bottom ChoiceFan.
const PER_CHARACTER_KINDS = new Set(["start_conversation", "introduce_to"]);
// Action kinds that move the player; surfaced through the location switcher.
const MOVE_KINDS = new Set(["move"]);

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
  // Free-time choices get split into three lanes: per-character (revealed by
  // tapping the character), location moves (revealed by the map button), and
  // everything else (rendered in the bottom ChoiceFan). When a minigame or
  // conversation is in flight, all actions stay in the ChoiceFan so the user
  // doesn't have to hunt for them.
  const inDialogue = state.active_conversation_target_id !== null;
  const inChallenge = state.pending_challenge !== null;
  const inIntros = state.phase === "intros";
  // The character-tap + location-switcher menus only make sense during
  // free-time. During intros / conversations / minigames we keep every
  // legal action in the bottom ChoiceFan / scripted beat queue.
  const useLanedActions = !inDialogue && !inChallenge && !inIntros;
  const characterActions = useMemo(
    () => useLanedActions ? actions.filter((a) => PER_CHARACTER_KINDS.has(a.kind) && a.target_id) : [],
    [actions, useLanedActions],
  );
  const moveActions = useMemo(
    () => useLanedActions ? actions.filter((a) => MOVE_KINDS.has(a.kind)) : [],
    [actions, useLanedActions],
  );
  const fanActions = useMemo(
    () =>
      useLanedActions
        ? actions.filter((a) => !PER_CHARACTER_KINDS.has(a.kind) && !MOVE_KINDS.has(a.kind))
        : actions,
    [actions, useLanedActions],
  );
  const [openCharacterId, setOpenCharacterId] = useState<string | null>(null);
  const [moveOpen, setMoveOpen] = useState(false);
  const plannedBeats = useMemo(
    () => locked
      ? pendingBeats(state, pendingActionLabel, streamText, streamSpeaker)
      : planScene(null, state, lastTurn, fanActions),
    [fanActions, lastTurn, locked, pendingActionLabel, state, streamSpeaker, streamText],
  );
  const [beatIndex, setBeatIndex] = useState(0);
  const sceneKey = `${state.turn_index}:${state.phase}:${lastTurn?.state_hash ?? "start"}:${locked ? "locked" : "ready"}:${actions.length}`;

  useEffect(() => setBeatIndex(0), [sceneKey]);
  useEffect(() => { setOpenCharacterId(null); setMoveOpen(false); }, [sceneKey]);

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

  const charactersWithActions = useMemo(() => {
    const ids = new Set<string>();
    characterActions.forEach((a) => { if (a.target_id) ids.add(a.target_id); });
    return ids;
  }, [characterActions]);
  const openCharacter = openCharacterId
    ? state.islanders.find((i) => i.id === openCharacterId) ?? null
    : null;
  const openCharacterActions = useMemo(
    () => openCharacterId
      ? characterActions.filter((a) => a.target_id === openCharacterId)
      : [],
    [characterActions, openCharacterId],
  );

  const sceneLocation = state.phase === "intros" ? "firepit" : state.location_id;
  return (
    <SceneLayer location={sceneLocation} onTap={() => {
      if (openCharacterId) { setOpenCharacterId(null); return; }
      if (moveOpen) { setMoveOpen(false); return; }
      advance();
    }}>
      <CharacterLayer
        state={state}
        focusedId={focusedId}
        speakerPose={speakerPose}
        tappableIds={charactersWithActions}
        onCharacterTap={(id) => { setMoveOpen(false); setOpenCharacterId((current) => current === id ? null : id); }}
      />
      {showBanner(state.pending_challenge, actions) ? (
        <ChallengeBanner pending={state.pending_challenge as PendingChallengeView} />
      ) : null}
      {moveActions.length > 0 ? (
        <MoveButton
          label={state.location_label}
          open={moveOpen}
          onToggle={() => { setOpenCharacterId(null); setMoveOpen((v) => !v); }}
          actions={moveOpen ? moveActions : []}
          locked={locked}
          onChoose={(action) => { setMoveOpen(false); onChoose(action); }}
        />
      ) : null}
      {openCharacter && openCharacterActions.length > 0 ? (
        <CharacterMenu
          name={openCharacter.name}
          position={positionById.get(openCharacter.id) ?? null}
          actions={openCharacterActions}
          locked={locked}
          onClose={() => setOpenCharacterId(null)}
          onChoose={(action) => { setOpenCharacterId(null); onChoose(action); }}
        />
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
      {useLanedActions && !openCharacterId && !moveOpen && characterActions.length > 0 && fanActions.length === 0 ? (
        <p className="scene-hint">Tap a Heartbreaker to chat, or use the map button to move.</p>
      ) : null}
      <style jsx>{`
        .scene-hint {
          position: absolute;
          left: 50%;
          bottom: 24px;
          transform: translateX(-50%);
          margin: 0;
          padding: 7px 14px 8px;
          border-radius: var(--r-pill);
          background: rgba(8,6,4,.62);
          border: 1px solid rgba(217,167,58,.32);
          color: var(--ink-on-dark);
          font-size: 12px;
          letter-spacing: .06em;
          font-style: italic;
          pointer-events: none;
          z-index: 6;
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
  const npcs = visibleNpcs(state, focusedId);
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

function MoveButton({
  label,
  open,
  onToggle,
  actions,
  locked,
  onChoose,
}: {
  label: string;
  open: boolean;
  onToggle: () => void;
  actions: AvailableAction[];
  locked: boolean;
  onChoose: (action: AvailableAction) => void;
}) {
  return (
    <div className="move-root">
      <button
        type="button"
        data-testid="move-button"
        className={`move-button${open ? " is-open" : ""}`}
        onClick={(e) => { e.stopPropagation(); onToggle(); }}
        aria-expanded={open}
        aria-haspopup="menu"
        disabled={locked}
      >
        <MapPin size={15} />
        <span className="move-label">{label}</span>
      </button>
      {open ? (
        <ul role="menu" className="move-menu" data-testid="move-menu" onClick={(e) => e.stopPropagation()}>
          {actions.map((action, index) => (
            <li key={`${action.kind}-${action.target_id}-${index}`} role="none">
              <button
                role="menuitem"
                type="button"
                className="move-item"
                disabled={locked}
                onClick={() => onChoose(action)}
              >
                {action.label.replace(/^Move to\s+/i, "")}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <style jsx>{`
        .move-root {
          position: absolute;
          top: 10px;
          right: 14px;
          z-index: 11;
        }
        .move-button {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          padding: 7px 12px 8px 11px;
          border-radius: var(--r-pill);
          background: rgba(20,16,12,.78);
          border: 1px solid rgba(217,167,58,.42);
          color: var(--card);
          font-family: var(--font-display);
          font-size: 13px;
          font-weight: 650;
          letter-spacing: .02em;
          backdrop-filter: blur(8px);
          box-shadow: var(--shadow-md);
          cursor: pointer;
          transition: background .15s, border-color .15s;
        }
        .move-button:hover:not(:disabled) {
          background: rgba(217,167,58,.18);
          border-color: rgba(217,167,58,.75);
        }
        .move-button:disabled { opacity: .55; cursor: not-allowed; }
        .move-button.is-open { background: rgba(217,167,58,.22); border-color: rgba(217,167,58,.78); }
        .move-label { text-transform: capitalize; }
        .move-menu {
          position: absolute;
          right: 0;
          top: calc(100% + 6px);
          margin: 0;
          padding: 6px;
          list-style: none;
          min-width: 180px;
          border-radius: var(--r-lg);
          background: rgba(20,16,12,.92);
          border: 1px solid rgba(217,167,58,.42);
          box-shadow: var(--shadow-lg), var(--inset-gold);
          backdrop-filter: blur(10px);
          display: grid;
          gap: 2px;
        }
        .move-item {
          width: 100%;
          padding: 8px 10px;
          border-radius: var(--r-md);
          background: transparent;
          border: 0;
          color: var(--ink-on-dark);
          font-family: var(--font-display);
          font-size: 14px;
          text-align: left;
          text-transform: capitalize;
          cursor: pointer;
          transition: background .12s;
        }
        .move-item:hover:not(:disabled) { background: rgba(217,167,58,.18); color: var(--card); }
        .move-item:disabled { opacity: .55; cursor: not-allowed; }
        @media (max-width: 520px) {
          .move-root { top: 6px; right: 8px; }
          .move-button { font-size: 12px; padding: 6px 10px 7px 9px; }
        }
      `}</style>
    </div>
  );
}

function CharacterMenu({
  name,
  position,
  actions,
  locked,
  onClose,
  onChoose,
}: {
  name: string;
  position: Position | null;
  actions: AvailableAction[];
  locked: boolean;
  onClose: () => void;
  onChoose: (action: AvailableAction) => void;
}) {
  const left = position ? Math.min(80, Math.max(20, position.x)) : 50;
  const top = position ? Math.min(72, Math.max(14, position.y - 22)) : 38;
  // Two-level tree: pick a category, then a specific intent. Intros are flat
  // (their 4 dynamics ARE the leaves) — auto-fire when there's only one
  // option per category.
  const grouped = useMemo(() => groupActionsByCategory(actions), [actions]);
  const [openCategory, setOpenCategory] = useState<IntentCategory | null>(null);
  const subActions = openCategory ? grouped[openCategory] : [];
  return (
    <div
      data-testid="character-menu"
      className="char-menu"
      style={{ left: `${left}%`, top: `${top}%` }}
      onClick={(e) => e.stopPropagation()}
    >
      <header>
        {openCategory ? (
          <button
            type="button"
            className="char-menu-back"
            aria-label="Back to categories"
            onClick={() => setOpenCategory(null)}
          >
            <ChevronLeft size={14} /> Back
          </button>
        ) : (
          <span className="char-menu-eyebrow">Talk to</span>
        )}
        <h3>{name}</h3>
        <button type="button" className="char-menu-close" onClick={onClose} aria-label="Close">
          <X size={14} />
        </button>
      </header>
      {openCategory ? (
        <ul role="menu" data-level="sub">
          {subActions.map((action, index) => (
            <li key={`${action.kind}-${action.intent_id}-${index}`} role="none">
              <button
                role="menuitem"
                type="button"
                className="char-menu-item"
                disabled={locked}
                onClick={() => onChoose(action)}
              >
                <span className="char-menu-label">{stripTalkPrefix(action.label, name)}</span>
                {action.audience_hint || action.risk ? (
                  <span className="char-menu-meta">
                    {action.audience_hint === "+" ? <i className="hint hint-good">Pulse +</i> : null}
                    {action.audience_hint === "-" ? <i className="hint hint-bad">Pulse -</i> : null}
                    {action.risk ? <i>{action.risk}</i> : null}
                  </span>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <ul role="menu" data-level="categories">
          {ORDERED_CATEGORIES.map((category) => {
            const categoryActions = grouped[category];
            const hasOptions = categoryActions.length > 0;
            const hint = CATEGORY_LOCK_HINT[category];
            // If a category has exactly one option, fire directly on click
            // (skip the sub-level). Otherwise expand.
            const onClick = !hasOptions
              ? undefined
              : categoryActions.length === 1
                ? () => onChoose(categoryActions[0])
                : () => setOpenCategory(category);
            return (
              <li key={category} role="none">
                <button
                  role="menuitem"
                  type="button"
                  className={`char-menu-item char-menu-category cat-${category}${hasOptions ? "" : " is-locked"}`}
                  disabled={locked || !hasOptions}
                  data-category={category}
                  onClick={onClick}
                >
                  <span className="char-menu-row">
                    <span className="char-menu-label">{CATEGORY_LABEL[category]} {name}</span>
                    {hasOptions ? (
                      <span className="char-menu-count">{categoryActions.length}</span>
                    ) : (
                      <Lock size={13} aria-hidden />
                    )}
                  </span>
                  {!hasOptions && hint ? <span className="char-menu-hint">{hint}</span> : null}
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <style jsx>{`
        .char-menu {
          position: absolute;
          z-index: 12;
          transform: translate(-50%, -100%);
          width: min(320px, calc(100vw - 24px));
          padding: 12px 14px 14px;
          border-radius: var(--r-xl);
          background: linear-gradient(180deg, rgba(248,246,239,.98), rgba(238,226,201,.96));
          border: 1px solid rgba(217,167,58,.55);
          box-shadow: var(--shadow-lg), var(--inset-gold);
          color: var(--ink);
          animation: pop .18s cubic-bezier(.22,.61,.36,1);
        }
        @keyframes pop {
          from { opacity: 0; transform: translate(-50%, -94%) scale(.96); }
          to { opacity: 1; transform: translate(-50%, -100%) scale(1); }
        }
        header { position: relative; display: grid; gap: 2px; margin-bottom: 8px; }
        .char-menu-eyebrow {
          font-family: var(--font-hand);
          font-size: 11px;
          letter-spacing: .14em;
          text-transform: uppercase;
          color: var(--accent-deep);
        }
        header h3 { margin: 0; font-family: var(--font-display); font-size: 20px; font-weight: 650; }
        .char-menu-close {
          position: absolute;
          top: -2px;
          right: -2px;
          display: grid;
          place-items: center;
          width: 24px;
          height: 24px;
          border-radius: var(--r-pill);
          background: transparent;
          border: 1px solid rgba(73,57,42,.22);
          color: rgba(73,57,42,.7);
          cursor: pointer;
        }
        .char-menu-close:hover { background: rgba(73,57,42,.1); color: var(--ink); }
        ul { list-style: none; padding: 0; margin: 0; display: grid; gap: 4px; }
        .char-menu-item {
          width: 100%;
          padding: 9px 11px 10px;
          border-radius: var(--r-md);
          background: rgba(255,255,255,.6);
          border: 1px solid rgba(217,167,58,.3);
          color: var(--ink);
          text-align: left;
          cursor: pointer;
          transition: background .12s, border-color .12s, transform .12s;
        }
        .char-menu-item:hover:not(:disabled) {
          background: rgba(255,255,255,.95);
          border-color: rgba(217,167,58,.6);
          transform: translateY(-1px);
        }
        .char-menu-item:disabled { opacity: .55; cursor: not-allowed; }
        .char-menu-label {
          display: block;
          font-family: var(--font-display);
          font-size: 14px;
          font-weight: 650;
          line-height: 1.22;
        }
        .char-menu-meta {
          display: flex;
          gap: 6px;
          margin-top: 4px;
        }
        .char-menu-meta i {
          font-style: normal;
          font-size: 10px;
          font-weight: 700;
          letter-spacing: .1em;
          text-transform: uppercase;
          color: rgba(73,57,42,.65);
        }
        .hint-good { color: #316844 !important; }
        .hint-bad { color: var(--accent-deep) !important; }
        .char-menu-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }
        .char-menu-count {
          font-size: 11px;
          font-weight: 700;
          padding: 2px 7px;
          border-radius: var(--r-pill);
          background: rgba(73,57,42,.12);
          color: rgba(73,57,42,.7);
          letter-spacing: .04em;
        }
        .char-menu-hint {
          display: block;
          margin-top: 4px;
          font-size: 11.5px;
          color: rgba(73,57,42,.7);
          font-style: italic;
          letter-spacing: .02em;
        }
        .char-menu-category.is-locked {
          opacity: .55;
          cursor: not-allowed;
        }
        .char-menu-category.is-locked .char-menu-label {
          color: rgba(73,57,42,.7);
        }
        .char-menu-category.cat-friendly { box-shadow: inset 3px 0 0 #d4a87a; }
        .char-menu-category.cat-flirty   { box-shadow: inset 3px 0 0 var(--accent); }
        .char-menu-category.cat-deep     { box-shadow: inset 3px 0 0 #c19a4f; }
        .char-menu-category.cat-banter   { box-shadow: inset 3px 0 0 #8aa580; }
        .char-menu-back {
          background: transparent;
          border: 0;
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 0;
          font-size: 12px;
          font-weight: 600;
          letter-spacing: .04em;
          text-transform: uppercase;
          color: var(--accent-deep);
          cursor: pointer;
        }
        .char-menu-back:hover { color: var(--ink); }
      `}</style>
    </div>
  );
}

function groupActionsByCategory(
  actions: AvailableAction[],
): Record<IntentCategory, AvailableAction[]> {
  const grouped: Record<IntentCategory, AvailableAction[]> = {
    friendly: [],
    flirty: [],
    deep: [],
    banter: [],
  };
  for (const action of actions) {
    grouped[categoryFor(action.intent_id)].push(action);
  }
  return grouped;
}

// Quiet reference to keep CATEGORY_SHORT exported usage intact.
void CATEGORY_SHORT;

function stripTalkPrefix(label: string, name: string): string {
  return label
    .replace(new RegExp(`^Talk to\\s+${escapeRegex(name)}\\s*[—:-]?\\s*`, "i"), "")
    .replace(new RegExp(`^Introduce yourself to\\s+${escapeRegex(name)}\\s*[—:-]?\\s*`, "i"), "")
    .replace(new RegExp(`^Greet\\s+${escapeRegex(name)}\\s*[—:-]?\\s*`, "i"), "")
    .trim() || label;
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
