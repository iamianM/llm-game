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
import { ChoiceMenu } from "./ChoiceMenu";
import { DialogueBox } from "./DialogueBox";
import { IntroPanel } from "./IntroPanel";
import { NpcPortrait } from "./NpcPortrait";
import { RightRail } from "../rail/RightRail";
import { TopBar } from "./TopBar";
import { VillaBackground } from "./VillaBackground";

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
  // When the player submits the LAST intro response, the engine auto-advances
  // the phase out of "intros" but the response carries the final NPC's reply.
  // Hold the IntroPanel mounted for that final exchange until the user clicks
  // Continue, so the reply is actually visible.
  const [holdIntrosForFinalReply, setHoldIntrosForFinalReply] = useState(false);
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
        onDialogueChunk: (chunk) => setStreamText((current) => current + chunk)
      });
    },
    onSuccess: (data) => {
      const prevPhase = lastTurn?.state.phase ?? query.data?.state.phase;
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
      // Intros just ended with a final-NPC exchange → hold the IntroPanel mounted
      // so the player can read that reply before the regular play UI takes over.
      if (prevPhase === "intros" && data.state.phase !== "intros" && data.exchange) {
        setHoldIntrosForFinalReply(true);
      }
      if (data.state.outcome) router.push(`/play/${sessionId}/finale`);
    }
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
  const target = state.active_conversation_target_id ?? lastTurn?.exchange?.speaker_id;
  const speaker = state.islanders.find((item) => item.id === target);
  const dialogue = lastTurn?.exchange;
  const event = lastTurn?.ceremony_events[0];
  const narration = ceremonyNarration(lastTurn, state);
  const latestRecap = state.daily_recaps[state.daily_recaps.length - 1];
  const dialogueText = mutation.isPending
    ? streamText || "Sunset Bay is reacting..."
    : dialogue?.npc_dialogue ?? stagePrompt(state, speaker?.name);
  const dialogueSpeaker = mutation.isPending ? streamSpeaker : dialogue?.speaker_name ?? speaker?.name ?? "The Producer";
  const playerLine = mutation.isPending ? pendingActionLabel ?? undefined : dialogue?.player_dialogue;

  const isIntros = state.phase === "intros" || holdIntrosForFinalReply;
  return (
    <main className="min-h-screen overflow-hidden bg-bg text-[var(--card)]">
      <TopBar state={state} onRail={() => setRail(true)} onSettings={() => setSettings(true)} />
      <div data-screen="stage" className="flex h-[calc(100vh-56px)] flex-col overflow-hidden">
        {isIntros ? (
          <IntroPanel
            state={state}
            actions={actions}
            pending={mutation.isPending}
            lastExchange={
              dialogue
                ? {
                    speakerId: dialogue.speaker_id,
                    playerLine: dialogue.player_dialogue,
                    npcLine: dialogue.npc_dialogue
                  }
                : null
            }
            onChoose={(action, playerLine) => {
              const enriched: AvailableAction = { ...action, label: playerLine };
              mutation.mutate(enriched);
            }}
            onIntrosDone={() => setHoldIntrosForFinalReply(false)}
          />
        ) : (
          <>
            <div className="flex-1 min-h-0 flex">
              <VillaBackground location={state.location_id}>
                {speaker ? <NpcPortrait npc={speaker} /> : <IdleStage location={state.location_label} phase={state.phase} />}
              </VillaBackground>
            </div>
            <DialogueBox
              speaker={dialogueSpeaker}
              playerLine={playerLine}
              text={dialogueText}
              complete={!mutation.isPending}
              audienceDelta={lastTurn?.audience_delta}
              audienceReason={lastTurn?.audience_delta_reason}
              onAdvance={() => {
                if (deferredCeremony) {
                  setDeferredCeremony(false);
                  setShowCeremony(true);
                }
              }}
            />
            <ChoiceMenu actions={actions} locked={mutation.isPending} onChoose={(action) => mutation.mutate(action)} />
          </>
        )}
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
    </main>
  );
}

function IdleStage({ location, phase }: { location: string; phase: string }) {
  return (
    <div className="idle-stage">
      <span className="idle-eyebrow">Sunset Bay</span>
      <h2 className="idle-place">{location || "Paradise"}</h2>
      <p className="idle-hint">{stagePrompt({ phase })}</p>
      <style jsx>{`
        .idle-stage {
          position: relative;
          display: grid;
          place-items: center;
          gap: 6px;
          padding: 22px 32px 24px;
          border-radius: var(--r-xl);
          background: linear-gradient(180deg, rgba(8,6,4,.55), rgba(8,6,4,.35));
          border: 1px solid rgba(217,167,58,.32);
          backdrop-filter: blur(10px);
          box-shadow: var(--shadow-stage), var(--inset-gold);
          color: var(--ink-on-dark);
          animation: drift-up 0.6s cubic-bezier(.22,.61,.36,1) both;
          min-width: 380px;
          text-align: center;
        }
        .idle-stage::before, .idle-stage::after {
          content: "";
          position: absolute;
          left: 50%; transform: translateX(-50%);
          width: 80px; height: 1px;
          background: linear-gradient(90deg, transparent, rgba(217,167,58,.45), transparent);
        }
        .idle-stage::before { top: 12px; }
        .idle-stage::after { bottom: 12px; }
        .idle-eyebrow {
          font-family: var(--font-hand);
          font-size: 20px;
          color: var(--gold-soft);
          letter-spacing: .04em;
          margin-top: 6px;
        }
        .idle-place {
          margin: 0;
          font-family: var(--font-display);
          font-size: 36px;
          font-weight: 600;
          letter-spacing: -.01em;
          color: var(--card);
          text-transform: capitalize;
        }
        .idle-hint {
          margin: 4px 0 6px;
          font-size: 13px;
          line-height: 1.55;
          color: var(--muted-on-dark);
          font-style: italic;
          max-width: 48ch;
        }
      `}</style>
    </div>
  );
}

function stagePrompt(state: { phase: string }, speakerName?: string) {
  if (speakerName) return `You're chatting with ${speakerName}. Choose your next response.`;
  if (state.phase === "intros") return "Day-1 introductions: meet each Heartbreaker once before free time opens.";
  if (state.phase === "morning") return "Choose your First Spark partner and see how the opening couples land.";
  return "Look around, Spark with someone, or let the day move.";
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
