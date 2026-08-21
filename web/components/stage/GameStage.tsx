"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { getSession, submitTurnStream } from "../../lib/api";
import type { AvailableAction, SessionResponse, SessionState, TurnResponse } from "../../lib/types";
import type { PresentationTransition, SceneFeature } from "../../lib/scene/presentation";
import { MINIGAME_SCENE_PRESENTATION } from "../../lib/minigame/scene-port";
import { playSfx } from "../../lib/sfx";
import { loadLook } from "../../lib/look";
import type { ArchetypeId, HeartbreakerLook } from "../../lib/look";
import { useUiStore } from "../../lib/store";
import { CeremonyOverlay } from "../ceremony/CeremonyOverlay";
import { DayRecap } from "../chrome/DayRecap";
import { SettingsMenu } from "../chrome/SettingsMenu";
import { WardrobeModal } from "../chrome/WardrobeModal";
import { RightRail } from "../rail/RightRail";
import { MinigameInsert } from "../minigame/MinigameInsert";
import { planScene } from "../scene/SceneDirector";
import { SceneDialogueStage } from "../scene/SceneDialogueStage";
import { TopBar } from "./TopBar";

type Props = {
  sessionId: string;
};

export function GameStage({ sessionId }: Props) {
  const router = useRouter();
  const [lastTurn, setLastTurn] = useState<TurnResponse | null>(null);
  const [previousState, setPreviousState] = useState<SessionState | null>(null);
  const [pendingAction, setPendingAction] = useState<AvailableAction | null>(null);
  const [streamText, setStreamText] = useState("");
  const [streamSpeakerName, setStreamSpeakerName] = useState<string | null>(null);
  const [featureQueue, setFeatureQueue] = useState<SceneFeature[]>([]);
  const [look, setLook] = useState<HeartbreakerLook | null>(null);
  const confirmedState = useRef<SessionState | null>(null);
  const seenFeatureIds = useRef(new Set<string>());
  const railOpen = useUiStore((s) => s.rightRailOpen);
  const setRail = useUiStore((s) => s.setRail);
  const setSettings = useUiStore((s) => s.setSettings);
  const setWardrobe = useUiStore((s) => s.setWardrobe);
  const setMusicScene = useUiStore((s) => s.setMusicScene);
  const reduce = useUiStore((s) => s.reduceMotion);
  const query = useQuery<SessionResponse>({ queryKey: ["session", sessionId], queryFn: () => getSession(sessionId), retry: false });
  const mutation = useMutation({
    mutationFn: (action: AvailableAction) => {
      if (!confirmedState.current) throw new Error("Cannot submit a turn before session state is loaded.");
      setPreviousState(confirmedState.current);
      setPendingAction(action);
      setStreamText("");
      setStreamSpeakerName(null);
      return submitTurnStream(sessionId, action, {
        onDialogueStart: (speaker) => setStreamSpeakerName(speaker),
        onDialogueChunk: (chunk) => setStreamText((current) => current + chunk),
      });
    },
    onSuccess: (data) => {
      setLastTurn(data);
      confirmedState.current = data.state;
      setStreamText("");
      setStreamSpeakerName(null);
      setPendingAction(null);
    },
    onError: () => {
      setPendingAction(null);
      setPreviousState(null);
      setStreamText("");
      setStreamSpeakerName(null);
    },
  });

  useEffect(() => {
    document.documentElement.classList.toggle("reduce-motion", reduce);
  }, [reduce]);
  // The look recipe lives in localStorage (see lib/look.ts); load it once the
  // session id is known so the in-scene player reflects the creator choices.
  useEffect(() => {
    setLook(loadLook(sessionId));
  }, [sessionId]);
  useEffect(() => {
    if (query.data && lastTurn === null) confirmedState.current = query.data.state;
  }, [query.data, lastTurn]);

  // Drive the background score from the live game phase: ceremonies and the
  // build-up to a challenge get the tense bed, nights get the evening bed, and
  // ordinary Sunset Bay daytime gets the warm day bed. Leaving the run resets the
  // app-wide player back to the title theme.
  const liveState = lastTurn?.state ?? query.data?.state;
  const livePhase = liveState?.phase;
  const liveTension = Boolean(
    featureQueue[0]?.kind === "ceremony" || liveState?.pending_challenge || liveState?.pending_pair_proposal,
  );
  useEffect(() => {
    if (!livePhase) return;
    if (liveTension) setMusicScene("tension");
    else if (livePhase === "evening") setMusicScene("evening");
    else setMusicScene("day");
  }, [livePhase, liveTension, setMusicScene]);
  useEffect(() => () => setMusicScene("title"), [setMusicScene]);

  useEffect(() => {
    if (featureQueue[0]?.kind === "ceremony") playSfx("ceremony-reveal");
  }, [featureQueue]);
  // Paradise Calls — chime when Sunset Bay drops into the daily notice
  // phase, the moment a producer message or gather is announced.
  const prevPhaseRef = useRef<string | undefined>(undefined);
  useEffect(() => {
    if (livePhase && livePhase !== prevPhaseRef.current && livePhase === "text") {
      playSfx("text-alert");
    }
    prevPhaseRef.current = livePhase;
  }, [livePhase]);

  if (query.isLoading) return <main className="grid min-h-screen place-items-center bg-bg text-[var(--card)]">Loading Paradise...</main>;
  if (query.error || !query.data) return <main className="grid min-h-screen place-items-center bg-bg text-[var(--card)]">Session not found.</main>;

  const state = lastTurn?.state ?? query.data.state;
  const actions = lastTurn?.available_actions ?? query.data.available_actions;
  const transition: PresentationTransition = mutation.isPending && pendingAction && previousState
    ? {
        kind: "pending",
        previous: previousState,
        state: previousState,
        actions,
        selectedAction: pendingAction,
        stream: {
          speakerId: null,
          speakerName: streamSpeakerName,
          text: streamText,
        },
      }
    : lastTurn && previousState
      ? { kind: "resolved", previous: previousState, response: lastTurn }
      : { kind: "baseline", state, actions };
  const scenePlan = planScene(transition, MINIGAME_SCENE_PRESENTATION);
  const activeFeature = featureQueue[0];
  const event = activeFeature?.kind === "ceremony" ? activeFeature.event : undefined;
  const narration = ceremonyNarration(lastTurn, state, event);
  const subjectLabels = Object.fromEntries([
    [state.player.id, state.player.name || "You"],
    ...state.heartbreakers.map((heartbreaker) => [heartbreaker.id, heartbreaker.name]),
  ]);
  const closeActiveFeature = () => {
    const hasMore = featureQueue.length > 1;
    setFeatureQueue((current) => current.slice(1));
    if (!hasMore && state.outcome) router.push(`/play/${sessionId}/finale`);
  };

  return (
    <main className="min-h-screen overflow-hidden bg-bg text-[var(--card)]">
      <TopBar state={state} onRail={() => setRail(true)} onSettings={() => setSettings(true)} onWardrobe={() => setWardrobe(true)} />
      <div data-screen="stage" className="stage-shell flex flex-col overflow-hidden">
        <div className="flex-1 min-h-0">
          <SceneDialogueStage
            state={state}
            plan={scenePlan}
            look={look}
            locked={mutation.isPending}
            onChoose={(action) => {
              playSfx("ui-click");
              mutation.mutate(action);
            }}
            onSettled={(features) => {
              const fresh = features.filter((feature) => {
                if (seenFeatureIds.current.has(feature.id)) return false;
                seenFeatureIds.current.add(feature.id);
                return true;
              });
              if (fresh.length > 0) {
                setFeatureQueue((current) => [...current, ...fresh]);
              } else if (state.outcome) {
                router.push(`/play/${sessionId}/finale`);
              }
            }}
            renderSlot={(slot) => (
              <MinigameInsert presentation={slot} subjectLabels={subjectLabels} />
            )}
          />
          {mutation.error ? (
            <p role="alert" className="turn-error">
              That choice did not land. Try it again in a moment.
            </p>
          ) : null}
        </div>
      </div>
      <RightRail state={state} sessionId={sessionId} open={railOpen} onClose={() => setRail(false)} look={look} />
      <SettingsMenu />
      <WardrobeModal
        sessionId={sessionId}
        currentLook={look}
        identity={{
          name: state.player.name,
          gender: state.player.gender,
          archetype: (state.player.archetype_id as ArchetypeId) ?? "heartthrob",
        }}
        onApply={(next) => setLook(next)}
      />
      {activeFeature?.kind === "ceremony" ? (
        <CeremonyOverlay
          title={ceremonyTitle(event, state)}
          eyebrow={ceremonyEyebrow(event)}
          narration={narration}
          couples={state.couples}
          showCouples={ceremonyShowsCouples(event, state)}
          onContinue={closeActiveFeature}
          playerId={state.player.id}
          playerLook={look}
        />
      ) : null}
      {activeFeature?.kind === "recap" ? (
        <DayRecap
          recap={activeFeature.recap}
          onClose={closeActiveFeature}
        />
      ) : null}
      <style jsx>{`
        /* The stage must fill the space below the 56px TopBar WITHOUT spilling
           past the visible viewport. Mobile browsers report 100vh as the
           "large" height (URL bar / toolbar hidden), so a 100vh-based stage runs
           taller than what's on screen and the bottom-anchored ChoiceFan lands
           behind the browser chrome. 100svh ("small" viewport height) measures
           the worst case with chrome shown, so the action cards always fit. The
           100vh line is a fallback for the rare browser without svh support. */
        .stage-shell {
          height: calc(100vh - 56px);
          height: calc(100svh - 56px);
        }
        .turn-error {
          position: fixed;
          left: 50%;
          bottom: 88px;
          z-index: 50;
          transform: translateX(-50%);
          max-width: min(520px, calc(100vw - 28px));
          margin: 0;
          padding: 10px 14px;
          border: 1px solid rgba(217,167,58,.42);
          border-radius: var(--r-md);
          background: rgba(20,16,12,.92);
          box-shadow: var(--shadow-md), var(--inset-gold);
          color: var(--card);
          text-align: center;
        }
      `}</style>
    </main>
  );
}

const FLUSH_KINDS = new Set(["flush_of_hearts_arrival", "flush_of_hearts_decision"]);
const COUPLE_REVEAL_KINDS = new Set([
  "pairing",
  "partner_stolen",
  "flush_of_hearts_return_reveal",
  "final_vote",
]);

function ceremonyTitle(event: Record<string, unknown> | undefined, state: SessionResponse["state"]) {
  const kind = String(event?.kind ?? "");
  if (kind === "pair_proposal" || kind.startsWith("npc_proposal")) return "Heart Swap Proposal";
  if (kind === "private_suite") return "Paradise Suite";
  if (kind === "flush_of_hearts_return_reveal") return "Sunset Bay Return";
  if (FLUSH_KINDS.has(kind)) return "Flush of Hearts";
  if (kind === "elimination") return "Heart Out";
  if (kind === "final_vote") return "Final Vote";
  if (state.day === 1 && state.couples.some((couple) => couple.formed_via_label === "First Spark")) return "First Spark";
  return "Pairing Ceremony";
}

function ceremonyEyebrow(event: Record<string, unknown> | undefined) {
  const kind = String(event?.kind ?? "");
  if (kind === "private_suite") return "A Night Away";
  if (kind === "pair_proposal" || kind.startsWith("npc_proposal")) return "A Choice Lands";
  if (kind === "flush_of_hearts_return_reveal") return "Flush of Hearts";
  if (FLUSH_KINDS.has(kind)) return "Flush of Hearts";
  if (kind === "final_vote") return "The Last Text";
  return "At the Flame Deck";
}

function ceremonyShowsCouples(event: Record<string, unknown> | undefined, state: SessionResponse["state"]) {
  const kind = String(event?.kind ?? "");
  if (COUPLE_REVEAL_KINDS.has(kind)) return true;
  if (state.day === 1 && state.couples.some((couple) => couple.formed_via_label === "First Spark")) return true;
  return false;
}

function ceremonyNarration(
  turn: TurnResponse | null,
  state: SessionResponse["state"],
  event: Record<string, unknown> | undefined,
) {
  const message = typeof event?.message === "string" ? event.message : "";
  if (message) return message;
  const prose = turn?.event_narration?.prose;
  if (typeof prose === "string" && prose.trim()) return prose;
  if (state.day === 1 && state.couples.some((couple) => couple.formed_via_label === "First Spark")) {
    return `At Sunset Bay, the First Spark locks in the first couples. ${coupleSentence(state)}`;
  }
  return `Everyone gathers at Sunset Bay as the night changes the field. ${coupleSentence(state)}`;
}

function coupleSentence(state: SessionResponse["state"]) {
  const names = state.couples.map((couple) => `${couple.partner_a_name} and ${couple.partner_b_name}`);
  if (!names.length) return "All eyes are on what happens next.";
  return `Tonight's couples: ${names.join("; ")}.`;
}
