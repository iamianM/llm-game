"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getSession, submitTurnStream } from "../../lib/api";
import type { AvailableAction, SessionResponse, TurnResponse } from "../../lib/types";
import { useUiStore } from "../../lib/store";
import { CeremonyOverlay } from "../ceremony/CeremonyOverlay";
import { DayRecap } from "../chrome/DayRecap";
import { SettingsMenu } from "../chrome/SettingsMenu";
import { RightRail } from "../rail/RightRail";
import { SceneDialogueStage } from "../scene/SceneDialogueStage";
import { TopBar } from "./TopBar";

export function GameStage({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const [lastTurn, setLastTurn] = useState<TurnResponse | null>(null);
  const [showCeremony, setShowCeremony] = useState(false);
  const [showRecap, setShowRecap] = useState(false);
  const [seenRecaps, setSeenRecaps] = useState(0);
  const [streamText, setStreamText] = useState("");
  const [streamSpeaker, setStreamSpeaker] = useState("Producer");
  const [pendingActionLabel, setPendingActionLabel] = useState<string | null>(null);
  const [deferredCeremony, setDeferredCeremony] = useState(false);
  const railOpen = useUiStore((s) => s.rightRailOpen);
  const setRail = useUiStore((s) => s.setRail);
  const setSettings = useUiStore((s) => s.setSettings);
  const reduce = useUiStore((s) => s.reduceMotion);
  const query = useQuery<SessionResponse>({ queryKey: ["session", sessionId], queryFn: () => getSession(sessionId), retry: false });
  const mutation = useMutation({
    mutationFn: (action: AvailableAction) => {
      setStreamText("");
      setStreamSpeaker("Producer");
      setPendingActionLabel(action.label);
      setDeferredCeremony(false);
      return submitTurnStream(sessionId, action, {
        onDialogueStart: (speaker) => setStreamSpeaker(speaker),
        onDialogueChunk: (chunk) => setStreamText((current) => current + chunk),
      });
    },
    onSuccess: (data) => {
      setLastTurn(data);
      setStreamText("");
      setPendingActionLabel(null);
      const hasCeremony = data.ceremony_events.length > 0;
      const hasDialogue = data.exchange !== null;
      setDeferredCeremony(hasCeremony && hasDialogue);
      setShowCeremony(hasCeremony && !hasDialogue);
      if (data.state.daily_recaps.length > seenRecaps) {
        setShowRecap(true);
        setSeenRecaps(data.state.daily_recaps.length);
      }
      if (data.state.outcome) router.push(`/play/${sessionId}/finale`);
    },
  });

  useEffect(() => {
    document.documentElement.classList.toggle("reduce-motion", reduce);
  }, [reduce]);
  useEffect(() => {
    if (query.data && lastTurn === null) setSeenRecaps(query.data.state.daily_recaps.length);
  }, [query.data, lastTurn]);

  if (query.isLoading) return <main className="grid min-h-screen place-items-center bg-bg text-[var(--card)]">Loading Paradise...</main>;
  if (query.error || !query.data) return <main className="grid min-h-screen place-items-center bg-bg text-[var(--card)]">Session not found.</main>;

  const state = lastTurn?.state ?? query.data.state;
  const actions = lastTurn?.available_actions ?? query.data.available_actions;
  const event = lastTurn?.ceremony_events[0];
  const narration = ceremonyNarration(lastTurn, state);
  const latestRecap = state.daily_recaps[state.daily_recaps.length - 1];

  return (
    <main className="min-h-screen overflow-hidden bg-bg text-[var(--card)]">
      <TopBar state={state} onRail={() => setRail(true)} onSettings={() => setSettings(true)} />
      <div data-screen="stage" className="flex h-[calc(100vh-56px)] flex-col overflow-hidden">
        <div className="flex-1 min-h-0">
          <SceneDialogueStage
            state={state}
            actions={actions}
            lastTurn={lastTurn}
            locked={mutation.isPending}
            pendingActionLabel={pendingActionLabel}
            streamText={streamText}
            streamSpeaker={streamSpeaker}
            onChoose={(action) => mutation.mutate(action)}
            onAdvance={() => {
              if (deferredCeremony) {
                setDeferredCeremony(false);
                setShowCeremony(true);
              }
            }}
          />
          {mutation.error ? (
            <p role="alert" className="turn-error">
              That choice did not land. Try it again in a moment.
            </p>
          ) : null}
        </div>
      </div>
      <RightRail state={state} sessionId={sessionId} open={railOpen} onClose={() => setRail(false)} />
      <SettingsMenu />
      {showCeremony ? (
        <CeremonyOverlay
          title={ceremonyTitle(event, state)}
          eyebrow={ceremonyEyebrow(event)}
          narration={narration}
          couples={state.couples}
          showCouples={ceremonyShowsCouples(event, state)}
          onContinue={() => setShowCeremony(false)}
        />
      ) : null}
      {showRecap && latestRecap && !showCeremony ? <DayRecap recap={latestRecap} onClose={() => setShowRecap(false)} /> : null}
      <style jsx>{`
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

const CASA_KINDS = new Set(["casa_amor_arrival", "casa_amor_decision"]);
const COUPLE_REVEAL_KINDS = new Set([
  "recoupling",
  "partner_stolen",
  "casa_amor_return_reveal",
  "final_vote",
]);

function ceremonyTitle(event: Record<string, unknown> | undefined, state: SessionResponse["state"]) {
  const kind = String(event?.kind ?? "");
  const subKind = String(event?.sub_kind ?? "");
  if (kind === "challenge") return displayEventName(subKind || kind);
  if (kind === "recouple_proposal") return "Heart Swap Proposal";
  if (kind === "casa_amor_return_reveal") return "Sunset Bay Return";
  if (CASA_KINDS.has(kind)) return "Flush of Hearts";
  if (kind === "producer_text" || kind === "gather_scheduled") return "Paradise Calls";
  if (kind === "elimination") return "Heart Out";
  if (kind === "final_vote") return "Final Vote";
  if (state.day === 1 && state.couples.some((couple) => couple.formed_via_label === "First Spark")) return "First Spark";
  return "Pairing Ceremony";
}

function ceremonyEyebrow(event: Record<string, unknown> | undefined) {
  const kind = String(event?.kind ?? "");
  if (kind === "challenge") return "Challenge Result";
  if (kind === "producer_text") return "A Text Lands";
  if (kind === "gather_scheduled") return "At the Firepit";
  if (kind === "casa_amor_return_reveal") return "Flush of Hearts";
  if (CASA_KINDS.has(kind)) return "Second Villa";
  if (kind === "final_vote") return "The Last Text";
  return "At the Firepit";
}

function ceremonyShowsCouples(event: Record<string, unknown> | undefined, state: SessionResponse["state"]) {
  const kind = String(event?.kind ?? "");
  if (COUPLE_REVEAL_KINDS.has(kind)) return true;
  if (state.day === 1 && state.couples.some((couple) => couple.formed_via_label === "First Spark")) return true;
  return false;
}

function ceremonyNarration(turn: TurnResponse | null, state: SessionResponse["state"]) {
  const prose = turn?.event_narration?.prose;
  if (typeof prose === "string" && prose.trim()) return prose;
  const event = turn?.ceremony_events[0];
  const message = typeof event?.message === "string" ? event.message : "";
  if (state.day === 1 && state.couples.some((couple) => couple.formed_via_label === "First Spark")) {
    return `At Sunset Bay, the First Spark locks in the first couples. ${coupleSentence(state)}`;
  }
  if (message) return message;
  return `Everyone gathers at Sunset Bay as the night changes the field. ${coupleSentence(state)}`;
}

function coupleSentence(state: SessionResponse["state"]) {
  const names = state.couples.map((couple) => `${couple.partner_a_name} and ${couple.partner_b_name}`);
  if (!names.length) return "All eyes are on what happens next.";
  return `Tonight's couples: ${names.join("; ")}.`;
}

function displayEventName(value: string) {
  const names: Record<string, string> = {
    challenge: "Challenge",
    compatibility_quiz: "Compatibility Quiz",
    final_couples: "Final Couples Challenge",
    heart_rate: "Pulse Race",
    lie_detector: "Lie Detector",
    mr_and_mrs: "The Couples Quiz",
    snog_marry_pie: "Kiss Wed Pass",
  };
  return names[value] ?? value.replaceAll("_", " ").replace(/\b\w/g, (match) => match.toUpperCase());
}
