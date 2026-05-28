"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import type { IslanderSummary, SessionResponse } from "../../lib/types";

type Props = {
  state: SessionResponse["state"];
  narration?: string | null;
  speakerName?: string | null;
};

const CHARACTER_IMAGE: Record<string, string> = {
  chloe: "/images/characters/chloe.webp",
  maya: "/images/characters/maya.webp",
  liam: "/images/characters/liam.webp",
  sophie_start: "/images/characters/sophie_start.webp",
  nia_start: "/images/characters/nia_start.webp",
  marcus_start: "/images/characters/marcus_start.webp",
  blake_start: "/images/characters/blake_start.webp",
  jordan_start: "/images/characters/jordan_start.webp",
  blake: "/images/characters/blake_start.webp",
  jordan: "/images/characters/jordan_start.webp",
  marcus: "/images/characters/marcus_start.webp",
  sophie: "/images/characters/sophie_start.webp",
  zara: "/images/characters/talia_ht.webp",
  nia: "/images/characters/nia_start.webp",
  sam_ht: "/images/characters/sam_ht.webp",
  riley_ht: "/images/characters/riley_ht.webp",
  ellis_ht: "/images/characters/ellis_ht.webp",
  talia_ht: "/images/characters/talia_ht.webp",
};

const ARCHETYPE_IMAGE: Record<string, string> = {
  heartthrob: "/images/archetypes/heartthrob.webp",
  class_clown: "/images/archetypes/class_clown.webp",
  loyal_friend: "/images/archetypes/loyal_friend.webp",
};

/**
 * Replaces the static "Sunset Bay / Firepit / Look around..." card. Renders
 * the cast as standing figures lined up in front of the firepit. Each
 * islander is a portrait-orientation standee that fades into the floor at
 * the bottom; their name sits beneath. The player gets the same treatment
 * using the chosen archetype's portrait. Latest narration scrolls in
 * underneath the figures.
 */
export function CastRing({ state, narration, speakerName }: Props) {
  const partners = new Map<string, string>();
  for (const couple of state.couples) {
    partners.set(couple.partner_a_id, couple.partner_b_id);
    partners.set(couple.partner_b_id, couple.partner_a_id);
  }
  const islanderTiles: IslanderSummary[] = state.islanders.filter(
    (i) => !i.eliminated && i.location_id === state.location_id && i.id !== "player",
  );
  const playerPartnerId = partners.get("player");
  islanderTiles.sort((a, b) => {
    if (a.id === playerPartnerId) return -1;
    if (b.id === playerPartnerId) return 1;
    return a.name.localeCompare(b.name);
  });

  const playerImage = ARCHETYPE_IMAGE[state.player.archetype_id] ?? null;

  return (
    <div className="cast-ring" data-testid="cast-ring">
      <div className="standee-row" role="list" aria-label="Heartbreakers in the scene">
        {/*
          The player is the camera/viewer, so they don't need their own tile
          standing in the firepit. The lineup is who YOU are looking at.
          We keep the archetype image computation around since it's the
          fallback if we ever need a player avatar elsewhere.
        */}
        {void playerImage}
        {islanderTiles.map((islander) => (
          <Standee
            key={islander.id}
            id={islander.id}
            name={islander.name}
            image={CHARACTER_IMAGE[islander.id] ?? null}
            role={islander.id === playerPartnerId ? "partner" : ""}
            isPartner={islander.id === playerPartnerId}
            isSpeaking={Boolean(speakerName && speakerName === islander.name)}
            isPlayer={false}
          />
        ))}
      </div>
      <NarrationScroll text={narration ?? null} />
      <style jsx>{`
        .cast-ring {
          position: relative;
          width: 100%;
          height: 100%;
          display: grid;
          grid-template-rows: 1fr auto;
          gap: 0;
        }
        .standee-row {
          display: flex;
          justify-content: center;
          align-items: end;
          gap: clamp(2px, 0.6vw, 8px);
          padding: 0 16px 0;
          align-self: end;
          overflow-x: auto;
          overflow-y: hidden;
          scrollbar-width: thin;
          scrollbar-color: rgba(217,167,58,.3) transparent;
        }
        .standee-row::-webkit-scrollbar { height: 4px; }
        .standee-row::-webkit-scrollbar-thumb { background: rgba(217,167,58,.3); }
        @media (max-width: 900px) {
          .standee-row { padding: 0 8px; }
        }
      `}</style>
    </div>
  );
}

function Standee({
  id,
  name,
  image,
  role,
  isPartner,
  isSpeaking,
  isPlayer,
}: {
  id: string;
  name: string;
  image: string | null;
  role: string;
  isPartner: boolean;
  isSpeaking: boolean;
  isPlayer: boolean;
}) {
  const classes = [
    "standee",
    isPartner ? "is-partner" : "",
    isSpeaking ? "is-speaking" : "",
    isPlayer ? "is-player" : "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={classes} role="listitem" aria-label={`${name}${role ? ` (${role})` : ""}`}>
      <div className="figure">
        {image ? (
          <Image
            src={image}
            alt={name}
            fill
            sizes="(max-width: 900px) 90px, 140px"
            className="figure-image"
            style={{ objectFit: "cover", objectPosition: "50% 12%" }}
            aria-hidden
          />
        ) : (
          <div className="figure-fallback" aria-hidden>
            {name.split(/\s+/).map((p) => p[0]).join("").slice(0, 2).toUpperCase()}
          </div>
        )}
        <div className="figure-fade" aria-hidden />
        {role ? <span className={`badge badge-${role.replace(/\s/g, "-")}`}>{role.toUpperCase()}</span> : null}
      </div>
      <span className="name">{name}</span>
      <style jsx>{`
        .standee {
          --w: clamp(72px, 9vw, 132px);
          --h: calc(var(--w) * 1.55);
          position: relative;
          display: grid;
          grid-template-rows: auto auto;
          justify-items: center;
          gap: 4px;
          transition: transform .25s cubic-bezier(.22,.61,.36,1);
        }
        .figure {
          position: relative;
          width: var(--w);
          height: var(--h);
          border-radius: 14px 14px 8px 8px;
          overflow: hidden;
          box-shadow: 0 14px 30px -10px rgba(0,0,0,.7);
          background: linear-gradient(180deg, rgba(28,22,16,.5), rgba(28,22,16,.2));
          border: 1px solid rgba(248,236,210,.10);
        }
        :global(.figure-image) {
          transform-origin: center top;
        }
        .figure-fallback {
          position: absolute; inset: 0;
          display: grid; place-items: center;
          background: linear-gradient(180deg, rgba(217,167,58,.35), rgba(120,80,40,.45));
          color: var(--card);
          font-family: var(--font-display);
          font-weight: 600;
          font-size: calc(var(--w) * 0.45);
          font-style: italic;
        }
        .figure-fade {
          position: absolute;
          left: 0; right: 0; bottom: 0;
          height: 40%;
          background: linear-gradient(180deg, transparent 0%, rgba(8,6,4,.55) 60%, rgba(8,6,4,.95) 100%);
          pointer-events: none;
        }
        .badge {
          position: absolute;
          left: 50%;
          top: 8px;
          transform: translateX(-50%);
          padding: 2px 8px;
          font-family: var(--font-hand);
          font-size: 10px;
          letter-spacing: .14em;
          text-transform: uppercase;
          border-radius: 99px;
          background: rgba(8,6,4,.65);
          backdrop-filter: blur(4px);
          color: var(--gold-soft);
          border: 1px solid rgba(217,167,58,.45);
        }
        .badge-partner {
          color: #f7e2dd;
          border-color: rgba(212,99,62,.65);
          background: rgba(193,75,58,.30);
        }
        .badge-you {
          color: #fff0d0;
          border-color: rgba(217,167,58,.85);
          background: rgba(40,28,16,.7);
        }
        .name {
          font-family: var(--font-display);
          font-weight: 500;
          font-size: clamp(11px, 1.1vw, 14px);
          color: var(--card);
          letter-spacing: .01em;
          text-shadow: 0 2px 8px rgba(0,0,0,.7);
        }
        /* Player gets a gold glow + a slight forward lift. */
        .is-player .figure {
          border-color: rgba(217,167,58,.7);
          box-shadow: 0 18px 34px -10px rgba(217,167,58,.4), 0 14px 30px -10px rgba(0,0,0,.7);
        }
        .is-player { transform: translateY(-4px); }
        /* Partner gets warm rim light. */
        .is-partner .figure {
          border-color: rgba(212,99,62,.55);
          box-shadow: 0 18px 30px -10px rgba(193,75,58,.35), 0 14px 30px -10px rgba(0,0,0,.7);
        }
        /* Currently speaking islander lifts and gold-glows. */
        .is-speaking { transform: translateY(-8px); }
        .is-speaking .figure {
          border-color: rgba(217,167,58,.85);
          box-shadow: 0 22px 40px -10px rgba(217,167,58,.5), 0 14px 30px -10px rgba(0,0,0,.7);
        }
      `}</style>
    </div>
  );
}

function NarrationScroll({ text }: { text: string | null }) {
  const [display, setDisplay] = useState<string | null>(text);
  const lastText = useRef<string | null>(null);
  useEffect(() => {
    if (text && text !== lastText.current) {
      lastText.current = text;
      setDisplay(text);
    }
  }, [text]);
  if (!display) {
    return (
      <div className="narration-empty">
        <p>Listen to the room. Pick a Heartbreaker to talk to, move villas, or let the producers move the day.</p>
        <style jsx>{`
          .narration-empty {
            display: grid; place-items: center;
            padding: 8px 16px;
            color: var(--muted-on-dark);
            font-size: 13px;
            font-style: italic;
          }
          .narration-empty p { margin: 0; max-width: 54ch; text-align: center; }
        `}</style>
      </div>
    );
  }
  return (
    <div className="narration-scroll" key={display} aria-live="polite">
      <p className="narration-text">{display}</p>
      <style jsx>{`
        .narration-scroll {
          padding: 12px 24px;
          background: linear-gradient(180deg, rgba(8,6,4,.85), rgba(8,6,4,.95));
          border-top: 1px solid rgba(217,167,58,.22);
          backdrop-filter: blur(6px);
          max-height: 22vh;
          overflow-y: auto;
          animation: drift-in 0.5s cubic-bezier(.22,.61,.36,1) both;
        }
        .narration-text {
          margin: 0 auto;
          max-width: 880px;
          color: var(--card);
          font-size: 15px;
          line-height: 1.55;
          font-style: italic;
        }
        @keyframes drift-in {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: none; }
        }
      `}</style>
    </div>
  );
}
