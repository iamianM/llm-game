"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { findOutfit, loadLook, type IslanderLook } from "../../lib/look";
import { playerSprite } from "../../lib/scene/player-sprite";
import type { SessionState } from "../../lib/types";
import { Avatar } from "../ui/Avatar";
import { Button } from "../ui/Button";

export function FinaleScreen({ state, sessionId }: { state: SessionState; sessionId?: string }) {
  const playerCouple = state.couples.find((couple) => couple.is_player_couple);
  const outcome = finaleOutcome(state.outcome);
  // Load the saved look so the player's own Islander — outfit accent and all —
  // shows up at their big moment instead of a generic initials disc.
  const [look, setLook] = useState<IslanderLook | null>(null);
  useEffect(() => {
    if (sessionId) setLook(loadLook(sessionId));
  }, [sessionId]);
  const playerId = state.player.id;
  const renderPartner = (id: string, name: string) =>
    id === playerId ? (
      <PlayerFinaleAvatar
        sprite={playerSprite(state.player.archetype_id, state.player.gender, look?.outfit, look?.characterId)}
        name={name}
        accent={look ? findOutfit(look.outfit).accent : "#ffe48a"}
      />
    ) : (
      <Avatar id={id} name={name} size="lg" />
    );
  return (
    <main data-screen="finale" className="finale-stage grid min-h-screen place-items-center bg-[linear-gradient(180deg,rgba(7,5,4,.4),rgba(7,5,4,.9)),url('/images/features/finale.webp')] bg-cover bg-center p-8 text-center text-[var(--card)]">
      <section className="finale-content max-w-3xl">
        <p className="finale-eyebrow font-hand text-4xl text-gold">Finale</p>
        <h1 className="finale-title mt-2 font-display text-7xl">{outcome.headline}</h1>
        {playerCouple ? (
          <div className="couple-card mx-auto mt-10 flex max-w-xl items-center justify-center gap-8 rounded-[var(--r-xl)] border border-gold bg-white/10 p-8">
            {renderPartner(playerCouple.partner_a_id, playerCouple.partner_a_name)}
            <div>
              <p className="font-display text-3xl">{playerCouple.partner_a_name} & {playerCouple.partner_b_name}</p>
              <p className="mt-2 text-gold">Connection score: {playerCouple.strength}/100</p>
            </div>
            {renderPartner(playerCouple.partner_b_id, playerCouple.partner_b_name)}
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

// The player's standee is a full-body transparent cutout. The NPCs in the
// couple card are tight face portraits (Avatar size="lg", 80px), so to keep the
// card balanced we frame the standee as a matching head-and-shoulders portrait:
// zoom the full-body image so only the upper body fills the 80px disc (tuned to
// land every archetype/gender's face cleanly), accented with the outfit ring.
function PlayerFinaleAvatar({ sprite, name, accent }: { sprite: string; name: string; accent: string }) {
  return (
    <div
      className="player-finale-avatar"
      aria-label={name}
      style={{ ["--accent" as string]: accent, backgroundImage: `url(${sprite})` }}
    >
      <style jsx>{`
        .player-finale-avatar {
          width: 80px;
          height: 80px;
          flex-shrink: 0;
          border-radius: 9999px;
          overflow: hidden;
          background-repeat: no-repeat;
          background-size: auto 380px;
          background-position: 46% 11%;
          background-color: color-mix(in srgb, var(--accent) 42%, #16110d);
          box-shadow: var(--shadow-md), 0 0 0 2px color-mix(in srgb, var(--accent) 70%, transparent), 0 0 22px color-mix(in srgb, var(--accent) 45%, transparent);
        }
      `}</style>
    </div>
  );
}

function finaleOutcome(outcome: SessionState["outcome"]) {
  switch (outcome) {
    case "won_as_couple":
      return {
        headline: "Sunset Bay has its winners",
        summary: "The villa fell for you, and the nation voted you home — you take the crown hand in hand.",
        reward: "The crowd sends you out with a roar.",
      };
    case "runner_up_couple":
      return {
        headline: "You made the final two",
        summary: "So close to the crown, and still standing together — the final two, no regrets.",
        reward: "The crowd remembers every moment you made.",
      };
    case "left_single":
      return {
        headline: "You leave Sunset Bay solo",
        summary: "No couple at the final this time, but you walk out with your head high and your story your own.",
        reward: "The villa carries your name long after you go.",
      };
    case "eliminated":
      return {
        headline: "Your summer ends tonight",
        summary: "The villa has spoken, and tonight you go Heart Out — carrying every memory you made here with you.",
        reward: "Sunset Bay keeps talking about you after you leave.",
      };
    default:
      return {
        headline: "Sunset Bay crowns its couple",
        summary: "The summer closes on Sunset Bay, and the lights stay warm for one last look.",
        reward: "The lights stay warm for one last look.",
      };
  }
}
