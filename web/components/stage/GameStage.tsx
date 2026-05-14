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
  const railOpen = useUiStore((s) => s.rightRailOpen);
  const setRail = useUiStore((s) => s.setRail);
  const setSettings = useUiStore((s) => s.setSettings);
  const reduce = useUiStore((s) => s.reduceMotion);
  const query = useQuery<SessionResponse>({ queryKey: ["session", sessionId], queryFn: () => getSession(sessionId), retry: false });
  const mutation = useMutation({
    mutationFn: (action: AvailableAction) => {
      setStreamText("");
      setStreamSpeaker("Producer");
      return submitTurnStream(sessionId, action, {
        onDialogueStart: (speaker) => setStreamSpeaker(speaker),
        onDialogueChunk: (chunk) => setStreamText((current) => current + chunk)
      });
    },
    onSuccess: (data) => {
      setLastTurn(data);
      setStreamText("");
      setShowCeremony(data.ceremony_events.length > 0);
      if (data.state.daily_recaps.length > seenRecaps) {
        setShowRecap(true);
        setSeenRecaps(data.state.daily_recaps.length);
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
  const dialogueText = mutation.isPending && streamText ? streamText : dialogue?.npc_dialogue ?? "Sunset Bay is waiting. Choose your next move.";
  const dialogueSpeaker = mutation.isPending && streamText ? streamSpeaker : dialogue?.speaker_name ?? "The Producer";

  return (
    <main className="min-h-screen overflow-hidden bg-bg text-[var(--card)]">
      <TopBar state={state} onRail={() => setRail(true)} onSettings={() => setSettings(true)} />
      <div data-screen="stage" className="flex h-[calc(100vh-56px)] flex-col">
        <VillaBackground location={state.location_id}>
          {speaker ? <NpcPortrait npc={speaker} /> : <IdleStage location={state.location_label} />}
        </VillaBackground>
        <DialogueBox
          speaker={dialogueSpeaker}
          playerLine={dialogue?.player_dialogue}
          text={dialogueText}
          complete={!mutation.isPending}
          audienceDelta={lastTurn?.audience_delta}
          audienceReason={lastTurn?.audience_delta_reason}
        />
        <ChoiceMenu actions={actions} locked={mutation.isPending} onChoose={(action) => mutation.mutate(action)} />
      </div>
      <RightRail state={state} sessionId={sessionId} open={railOpen} onClose={() => setRail(false)} />
      <SettingsMenu />
      {showCeremony ? <CeremonyOverlay title={ceremonyTitle(event, state)} narration={narration} couples={state.couples} onContinue={() => setShowCeremony(false)} /> : null}
      {showRecap && latestRecap && !showCeremony ? <DayRecap recap={latestRecap} onClose={() => setShowRecap(false)} /> : null}
    </main>
  );
}

function IdleStage({ location }: { location: string }) {
  return (
    <div className="rounded-[var(--r-lg)] border border-white/15 bg-black/25 px-8 py-6 text-center shadow-[var(--shadow-stage)]">
      <p className="font-hand text-4xl text-gold">Sunset Bay</p>
      <p className="mt-2 font-display text-3xl">{location}</p>
      <p className="mt-2 text-sm text-[var(--muted-on-dark)]">Look around, Spark with someone, or let the day move.</p>
    </div>
  );
}

function ceremonyTitle(event: Record<string, unknown> | undefined, state: SessionResponse["state"]) {
  const kind = String(event?.kind ?? "");
  if (kind === "recouple_proposal") return "Heart Swap Proposal";
  if (kind.includes("casa")) return "Flush of Hearts";
  if (kind === "producer_text" || kind === "gather_scheduled") return "Paradise Calls";
  if (kind === "elimination") return "Heart Out";
  if (state.day === 1 && state.couples.some((couple) => couple.formed_via_label === "First Spark")) return "First Spark";
  return "Pairing Ceremony";
}

function ceremonyNarration(turn: TurnResponse | null, state: SessionResponse["state"]) {
  const prose = turn?.event_narration?.prose;
  if (typeof prose === "string" && prose.trim() && !/completed\.?$/i.test(prose)) return prose;
  const event = turn?.ceremony_events[0];
  const message = typeof event?.message === "string" ? event.message : "";
  if (state.day === 1 && state.couples.some((couple) => couple.formed_via_label === "First Spark")) {
    return `At Sunset Bay, the First Spark locks in the first couples. ${coupleSentence(state)}`;
  }
  if (message && !/completed\.?$/i.test(message)) return message;
  return `Everyone gathers at Sunset Bay as the night changes the field. ${coupleSentence(state)}`;
}

function coupleSentence(state: SessionResponse["state"]) {
  const names = state.couples.map((couple) => `${couple.partner_a_name} and ${couple.partner_b_name}`);
  if (!names.length) return "All eyes are on what happens next.";
  return `Tonight's couples: ${names.join("; ")}.`;
}
