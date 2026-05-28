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
import { CastRing } from "./CastRing";
import { ChallengeSpectacle, type PendingChallengeView } from "./ChallengeSpectacle";
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
      // Intros just ended with a final-NPC exchange; hold the IntroPanel mounted
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
                {state.pending_challenge ? (
                  <ChallengeSpectacle
                    state={state}
                    pendingChallenge={state.pending_challenge as PendingChallengeView}
                  />
                ) : speaker ? (
                  <NpcPortrait npc={speaker} />
                ) : (
                  <CastRing
                    state={state}
                    narration={
                      (typeof lastTurn?.event_narration?.prose === "string"
                        ? lastTurn.event_narration.prose
                        : null) ??
                      lastTurn?.exchange?.npc_dialogue ??
                      null
                    }
                    speakerName={dialogue?.speaker_name ?? null}
                  />
                )}
              </VillaBackground>
            </div>
            {!isQuizActive(state) ? (
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
            ) : null}
            <QuizHeader pendingChallenge={state.pending_challenge as PendingChallengeView | null | undefined} />
            <QuizWrap pendingChallenge={state.pending_challenge as PendingChallengeView | null | undefined} />
            {mutation.error ? (
              <p role="alert" className="turn-error">
                That choice did not land. Try it again in a moment.
              </p>
            ) : null}
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
      <style jsx>{`
        .turn-error {
          position: fixed;
          left: 50%;
          bottom: calc(var(--choice-height, 120px) + 18px);
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

function stagePrompt(state: { phase: string; day?: number }, speakerName?: string) {
  if (speakerName) return `You're chatting with ${speakerName}. Choose your next response.`;
  if (state.phase === "intros") return "Day-1 introductions: meet each Heartbreaker once before free time opens.";
  if (state.phase === "morning" && state.day === 1) return "Choose your First Spark partner and see how the opening couples land.";
  if (state.phase === "morning") return "Morning in the villa: pick who gets your first real moment of the day.";
  return "Choose who to talk to, move around the villa, or let the day move.";
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

function isQuizActive(state: SessionResponse["state"]): boolean {
  const pc = state.pending_challenge as PendingChallengeView | null | undefined;
  if (!pc) return false;
  if (pc.finished) return true; // wrap panel takes the stage, hide DialogueBox
  return typeof pc.stem === "string" && pc.stem.length > 0;
}

function QuizHeader({ pendingChallenge }: { pendingChallenge: PendingChallengeView | null | undefined }) {
  if (!pendingChallenge || pendingChallenge.finished) return null;
  const { stem, round_index, round_count, kind, answered_rounds } = pendingChallenge;
  if (!stem) return null;
  const title = displayEventName(kind);
  // Last-round feedback: between rounds we show the previous round's
  // result so the player isn't waiting until the end to learn anything.
  const lastAnswered = answered_rounds && answered_rounds.length > 0
    ? answered_rounds[answered_rounds.length - 1]
    : null;
  const showLastResult = lastAnswered && typeof round_index === "number" && lastAnswered.round_index === round_index - 1;
  return (
    <div className="quiz-header" data-testid="quiz-header">
      {showLastResult ? (
        <div className={`last-round ${lastAnswered.is_correct ? "is-correct" : "is-wrong"}`}>
          <span className="last-mark">{lastAnswered.is_correct ? "Right" : "Wrong"}</span>
          <span className="last-detail">
            you said <strong>{lastAnswered.chosen_label}</strong>
            {!lastAnswered.is_correct && lastAnswered.correct_label
              ? <> — the truth was <strong>{lastAnswered.correct_label}</strong></>
              : null}
          </span>
          {lastAnswered.reaction_line ? (
            <span className="last-reaction">{lastAnswered.reaction_line}</span>
          ) : null}
        </div>
      ) : null}
      <div className="quiz-row">
        <span className="quiz-title">{title}</span>
        {typeof round_index === "number" && typeof round_count === "number" ? (
          <span className="quiz-round">Round {round_index + 1} of {round_count}</span>
        ) : null}
      </div>
      <h2 className="quiz-stem">{stem}</h2>
      <style jsx>{`
        .quiz-header {
          padding: 10px 18px 0;
          background: linear-gradient(180deg, rgba(8,6,4,.95), rgba(8,6,4,.95));
          border-top: 1px solid rgba(217,167,58,.18);
        }
        .quiz-row {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 14px;
          max-width: 1180px;
          margin: 0 auto 4px;
        }
        .quiz-title {
          font-family: var(--font-hand);
          color: var(--gold-soft);
          font-size: 13px;
          letter-spacing: .14em;
          text-transform: uppercase;
        }
        .quiz-round {
          font-size: 12px;
          color: var(--muted-on-dark);
          letter-spacing: .04em;
        }
        .quiz-stem {
          max-width: 1180px;
          margin: 0 auto;
          font-family: var(--font-display);
          font-size: 20px;
          line-height: 1.3;
          color: var(--ink-on-dark);
          padding-bottom: 6px;
        }
        .last-round {
          max-width: 1180px;
          margin: 0 auto 8px;
          padding: 8px 12px;
          border-radius: 10px;
          display: flex;
          flex-wrap: wrap;
          align-items: baseline;
          gap: 12px;
          animation: round-result-pop 0.35s cubic-bezier(.34,1.56,.64,1) both;
        }
        .is-correct { background: rgba(45,106,63,.18); border: 1px solid rgba(164,205,177,.45); }
        .is-wrong   { background: rgba(193,75,58,.18); border: 1px solid rgba(247,226,221,.45); }
        .last-mark {
          font-family: var(--font-hand);
          font-size: 14px;
          letter-spacing: .12em;
          text-transform: uppercase;
          font-weight: 600;
        }
        .is-correct .last-mark { color: var(--good-soft, #a4cdb1); }
        .is-wrong   .last-mark { color: var(--bad-soft, #f7e2dd); }
        .last-detail { font-size: 13px; color: var(--ink-on-dark); }
        .last-reaction { font-size: 13px; font-style: italic; color: var(--muted-on-dark); flex-basis: 100%; }
        @keyframes round-result-pop {
          from { transform: translateY(-6px); opacity: 0; }
          to   { transform: none; opacity: 1; }
        }
        @media (max-width: 700px) {
          .quiz-header { padding: 8px 12px 0; }
          .quiz-stem { font-size: 17px; }
        }
      `}</style>
    </div>
  );
}

const CLASSIFICATION_LABEL: Record<string, { label: string; tone: "good" | "mid" | "bad" }> = {
  success: { label: "Smashed it.", tone: "good" },
  partial: { label: "Got there in patches.", tone: "mid" },
  failure: { label: "Rough one.", tone: "bad" },
};

function QuizWrap({ pendingChallenge }: { pendingChallenge: PendingChallengeView | null | undefined }) {
  if (!pendingChallenge || !pendingChallenge.finished) return null;
  const { kind, classification, total_points, audience_delta, answered_rounds, round_count } = pendingChallenge;
  const title = displayEventName(kind);
  const verdict = classification ? CLASSIFICATION_LABEL[classification] : null;
  const correctCount = (answered_rounds ?? []).filter((r) => r.is_correct).length;
  return (
    <div className="quiz-wrap" data-testid="quiz-wrap">
      <header className="wrap-header">
        <div>
          <span className="wrap-title">{title} — wrap</span>
          {verdict ? <span className={`wrap-verdict tone-${verdict.tone}`}>{verdict.label}</span> : null}
        </div>
        <div className="wrap-stats">
          <span><strong>{correctCount}</strong> of <strong>{round_count ?? answered_rounds?.length ?? 0}</strong> right</span>
          {typeof total_points === "number" ? <span>· <strong>{total_points}</strong> pts</span> : null}
          {typeof audience_delta === "number" && audience_delta !== 0 ? (
            <span className={`wrap-audience ${audience_delta > 0 ? "tone-good" : "tone-bad"}`}>
              Audience {audience_delta > 0 ? "+" : ""}{audience_delta}
            </span>
          ) : null}
        </div>
      </header>
      <ol className="wrap-rounds">
        {(answered_rounds ?? []).map((r) => (
          <li key={r.round_index} className={`wrap-round ${r.is_correct ? "is-correct" : "is-wrong"}`}>
            <span className="round-num">R{r.round_index + 1}</span>
            <span className="round-mark">{r.is_correct ? "✓" : "✗"}</span>
            <div className="round-detail">
              <p className="round-stem">{r.stem}</p>
              <p className="round-answers">
                You said <strong>{r.chosen_label || "—"}</strong>
                {!r.is_correct && r.correct_label
                  ? <> · Truth was <strong>{r.correct_label}</strong></>
                  : null}
              </p>
              {r.reaction_line ? <p className="round-reaction">{r.reaction_line}</p> : null}
            </div>
          </li>
        ))}
      </ol>
      <style jsx>{`
        .quiz-wrap {
          padding: 14px 18px 8px;
          background: linear-gradient(180deg, rgba(8,6,4,.95), rgba(8,6,4,.9));
          border-top: 1px solid rgba(217,167,58,.22);
          max-height: 50vh;
          overflow-y: auto;
          animation: wrap-in 0.45s cubic-bezier(.22,.61,.36,1) both;
        }
        @keyframes wrap-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
        .wrap-header {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          gap: 14px;
          flex-wrap: wrap;
          max-width: 1180px;
          margin: 0 auto 8px;
        }
        .wrap-title {
          font-family: var(--font-hand);
          color: var(--gold-soft);
          font-size: 14px;
          letter-spacing: .14em;
          text-transform: uppercase;
          margin-right: 12px;
        }
        .wrap-verdict {
          font-family: var(--font-display);
          font-size: 18px;
          font-weight: 600;
        }
        .tone-good { color: var(--good-soft, #a4cdb1); }
        .tone-mid  { color: var(--gold-soft, #f4e3b8); }
        .tone-bad  { color: var(--bad-soft, #f7e2dd); }
        .wrap-stats { display: flex; gap: 10px; font-size: 13px; color: var(--muted-on-dark); flex-wrap: wrap; }
        .wrap-stats strong { color: var(--card); }
        .wrap-audience { padding: 2px 8px; border-radius: 99px; }
        .wrap-rounds {
          list-style: none;
          margin: 0 auto;
          padding: 0;
          max-width: 1180px;
          display: grid;
          gap: 8px;
        }
        .wrap-round {
          display: grid;
          grid-template-columns: auto auto 1fr;
          gap: 10px;
          align-items: start;
          padding: 8px 12px;
          border-radius: 10px;
          background: rgba(28,22,16,.55);
          border-left: 3px solid;
          animation: wrap-row-in 0.4s cubic-bezier(.22,.61,.36,1) both;
        }
        @keyframes wrap-row-in { from { opacity: 0; transform: translateX(-6px); } to { opacity: 1; transform: none; } }
        .wrap-round.is-correct { border-left-color: rgba(164,205,177,.7); }
        .wrap-round.is-wrong   { border-left-color: rgba(247,226,221,.7); }
        .round-num {
          font-family: var(--font-hand);
          color: var(--gold-soft);
          font-size: 12px;
          letter-spacing: .1em;
          padding-top: 1px;
        }
        .round-mark {
          font-size: 16px;
          font-weight: 700;
        }
        .is-correct .round-mark { color: var(--good-soft, #a4cdb1); }
        .is-wrong   .round-mark { color: var(--bad-soft, #f7e2dd); }
        .round-detail p { margin: 0; }
        .round-stem { font-size: 13px; color: var(--card); margin-bottom: 4px; line-height: 1.4; }
        .round-answers { font-size: 13px; color: var(--ink-on-dark); }
        .round-answers strong { color: var(--card); font-weight: 600; }
        .round-reaction { margin-top: 4px; font-size: 12px; font-style: italic; color: var(--muted-on-dark); }
      `}</style>
    </div>
  );
}
