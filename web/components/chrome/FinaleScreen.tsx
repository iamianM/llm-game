"use client";

import Link from "next/link";
import type { SessionState } from "../../lib/types";
import { Avatar } from "../ui/Avatar";
import { Button } from "../ui/Button";

export function FinaleScreen({ state }: { state: SessionState }) {
  const playerCouple = state.couples.find((couple) => couple.is_player_couple);
  const outcome = finaleOutcome(state.outcome);
  return (
    <main data-screen="finale" className="finale-stage grid min-h-screen place-items-center bg-[linear-gradient(180deg,rgba(7,5,4,.4),rgba(7,5,4,.9)),url('/images/features/finale.webp')] bg-cover bg-center p-8 text-center text-[var(--card)]">
      <section className="finale-content max-w-3xl">
        <p className="finale-eyebrow font-hand text-4xl text-gold">Finale</p>
        <h1 className="finale-title mt-2 font-display text-7xl">{outcome.headline}</h1>
        {playerCouple ? (
          <div className="couple-card mx-auto mt-10 flex max-w-xl items-center justify-center gap-8 rounded-[var(--r-xl)] border border-gold bg-white/10 p-8">
            <Avatar id={playerCouple.partner_a_id} name={playerCouple.partner_a_name} size="lg" />
            <div>
              <p className="font-display text-3xl">{playerCouple.partner_a_name} & {playerCouple.partner_b_name}</p>
              <p className="mt-2 text-gold">Connection score: {playerCouple.strength}/100</p>
            </div>
            <Avatar id={playerCouple.partner_b_id} name={playerCouple.partner_b_name} size="lg" />
          </div>
        ) : null}
        <p className="result-line mt-8 text-lg text-[var(--muted-on-dark)]">{outcome.summary}</p>
        <p className="mt-2 text-gold">{outcome.reward}</p>
        <Link href="/"><Button className="mt-8">New Run</Button></Link>
      </section>
      <style jsx>{`
        .finale-stage {
          position: relative;
          overflow: hidden;
          isolation: isolate;
        }
        .finale-stage::before {
          content: "";
          position: absolute;
          inset: 0;
          background:
            radial-gradient(48% 28% at 50% 48%, rgba(217,167,58,.22), transparent 68%),
            linear-gradient(90deg, transparent, rgba(248,236,210,.08), transparent);
          pointer-events: none;
          animation: finale-light 4s ease-in-out infinite;
        }
        .finale-content {
          position: relative;
          z-index: 1;
          animation: finale-rise .55s cubic-bezier(.22,.61,.36,1) both;
        }
        .finale-title {
          text-wrap: balance;
        }
        .couple-card {
          animation: couple-reveal .7s .16s cubic-bezier(.34,1.56,.64,1) both;
          backdrop-filter: blur(8px);
          box-shadow: var(--shadow-stage), 0 0 38px rgba(217,167,58,.22);
        }
        .result-line {
          animation: finale-rise .5s .24s cubic-bezier(.22,.61,.36,1) both;
        }
        @keyframes finale-light {
          0%, 100% { opacity: .7; transform: translateY(0); }
          50% { opacity: 1; transform: translateY(-8px); }
        }
        @keyframes finale-rise {
          from { opacity: 0; transform: translateY(16px); }
          to { opacity: 1; transform: none; }
        }
        @keyframes couple-reveal {
          from { opacity: 0; transform: translateY(18px) scale(.96); }
          to { opacity: 1; transform: none; }
        }
        @media (max-width: 720px) {
          .finale-title { font-size: clamp(42px, 13vw, 72px); }
          .couple-card {
            display: grid;
            grid-template-columns: auto 1fr auto;
            gap: 14px;
            padding: 18px;
          }
        }
      `}</style>
    </main>
  );
}

function finaleOutcome(outcome: SessionState["outcome"]) {
  switch (outcome) {
    case "won_as_couple":
      return {
        headline: "Sunset Bay has its winners",
        summary: "Final result: winners as a couple.",
        reward: "The crowd sends you out with a roar.",
      };
    case "runner_up_couple":
      return {
        headline: "You made the final two",
        summary: "Final result: runner-up couple.",
        reward: "The crowd remembers the moments you made.",
      };
    case "left_single":
      return {
        headline: "You leave Sunset Bay solo",
        summary: "Final result: left single.",
        reward: "The story ends on your own terms.",
      };
    case "eliminated":
      return {
        headline: "Your summer ends tonight",
        summary: "Final result: Heart Out.",
        reward: "The villa keeps talking after you leave.",
      };
    default:
      return {
        headline: "Sunset Bay crowns its couple",
        summary: "Final result: complete.",
        reward: "The lights stay warm for one last look.",
      };
  }
}
