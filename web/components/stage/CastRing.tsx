"use client";

import { useEffect, useRef, useState } from "react";
import { Avatar } from "../ui/Avatar";
import type { IslanderSummary, SessionResponse } from "../../lib/types";

type Props = {
  state: SessionResponse["state"];
  narration?: string | null;
  speakerName?: string | null;
};

/**
 * Replaces the old static "Sunset Bay / Firepit / Look around..." location
 * card. Shows the player + every NPC currently in the same location laid
 * out in a horizontal ring, with the latest narration scrolling underneath.
 * Gives the player a real sense of who's actually in the scene rather than
 * a place-name and a generic prompt.
 */
export function CastRing({ state, narration, speakerName }: Props) {
  const partners = new Map<string, string>();
  for (const couple of state.couples) {
    partners.set(couple.partner_a_id, couple.partner_b_id);
    partners.set(couple.partner_b_id, couple.partner_a_id);
  }
  // Filter islanders to whoever shares the player's current location and is
  // still in the game. villa_snapshot keys by display label, not id, so we
  // can't index into it — read location_id off each IslanderSummary instead.
  const islanderTiles: IslanderSummary[] = state.islanders.filter(
    (i) => !i.eliminated && i.location_id === state.location_id && i.id !== "player",
  );
  // Sort: partner first, then alphabetical by name.
  const playerPartnerId = partners.get("player");
  islanderTiles.sort((a, b) => {
    if (a.id === playerPartnerId) return -1;
    if (b.id === playerPartnerId) return 1;
    return a.name.localeCompare(b.name);
  });

  return (
    <div className="cast-ring" data-testid="cast-ring">
      <div className="ring-row" role="list" aria-label="Heartbreakers in the scene">
        <PlayerTile state={state} />
        {islanderTiles.map((islander) => (
          <CastTile
            key={islander.id}
            islander={islander}
            isPartner={islander.id === playerPartnerId}
            isSpeaking={Boolean(speakerName && speakerName === islander.name)}
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
          gap: 12px;
          padding: 16px 24px;
        }
        .ring-row {
          display: flex;
          flex-wrap: wrap;
          justify-content: center;
          align-items: end;
          gap: 14px;
          padding: 8px 4px;
          align-self: end;
        }
        @media (max-width: 720px) {
          .cast-ring { padding: 10px 12px; }
          .ring-row { gap: 8px; }
        }
      `}</style>
    </div>
  );
}

function PlayerTile({ state }: { state: SessionResponse["state"] }) {
  return (
    <div className="tile player-tile" role="listitem" aria-label={`${state.player.name} (you)`}>
      <div className="halo halo-player" aria-hidden />
      <div className="avatar-wrap"><Avatar id="player" name={state.player.name} size="responsive" /></div>
      <span className="name">{state.player.name || "You"}</span>
      <span className="role">you</span>
      <style jsx>{`
        .tile {
          position: relative;
          display: grid;
          grid-template-rows: auto auto auto;
          justify-items: center;
          gap: 4px;
          --tile-size: clamp(64px, 9vh, 96px);
        }
        .player-tile { transform: translateY(-4px); }
        .halo {
          position: absolute;
          left: 50%; top: 0;
          transform: translateX(-50%);
          width: calc(var(--tile-size) + 14px);
          height: calc(var(--tile-size) + 14px);
          border-radius: 999px;
          background: radial-gradient(circle, rgba(217,167,58,.30) 0%, transparent 60%);
          z-index: 0;
        }
        .avatar-wrap {
          position: relative;
          z-index: 1;
          width: var(--tile-size);
          height: var(--tile-size);
          border-radius: 999px;
          overflow: hidden;
          border: 2px solid rgba(217,167,58,.7);
          box-shadow: 0 6px 14px rgba(0,0,0,.45);
        }
        .name {
          font-family: var(--font-display);
          font-weight: 600;
          font-size: 14px;
          color: var(--card);
        }
        .role {
          font-family: var(--font-hand);
          font-size: 11px;
          letter-spacing: .08em;
          text-transform: uppercase;
          color: var(--gold-soft);
        }
      `}</style>
    </div>
  );
}

function CastTile({ islander, isPartner, isSpeaking }: { islander: IslanderSummary; isPartner: boolean; isSpeaking: boolean }) {
  const role = isPartner ? "partner" : "";
  return (
    <div
      className={`tile${isPartner ? " partner-tile" : ""}${isSpeaking ? " speaking" : ""}`}
      role="listitem"
      aria-label={`${islander.name}${isPartner ? " (partner)" : ""}`}
    >
      <div className="halo" aria-hidden />
      <div className="avatar-wrap"><Avatar id={islander.id} name={islander.name} size="responsive" /></div>
      <span className="name">{islander.name}</span>
      {role ? <span className="role">{role}</span> : <span className="role-spacer" aria-hidden />}
      <style jsx>{`
        .tile {
          position: relative;
          display: grid;
          grid-template-rows: auto auto auto;
          justify-items: center;
          gap: 4px;
          --tile-size: clamp(56px, 8vh, 84px);
          transition: transform .2s;
        }
        .partner-tile { --tile-size: clamp(60px, 8.5vh, 90px); }
        .speaking { transform: translateY(-6px); }
        .halo {
          position: absolute;
          left: 50%; top: 0;
          transform: translateX(-50%);
          width: calc(var(--tile-size) + 10px);
          height: calc(var(--tile-size) + 10px);
          border-radius: 999px;
          background: radial-gradient(circle, rgba(248,236,210,.10) 0%, transparent 60%);
          z-index: 0;
        }
        .partner-tile .halo {
          background: radial-gradient(circle, rgba(212,99,62,.30) 0%, transparent 60%);
        }
        .speaking .halo {
          background: radial-gradient(circle, rgba(217,167,58,.30) 0%, transparent 60%);
        }
        .avatar-wrap {
          position: relative;
          z-index: 1;
          width: var(--tile-size);
          height: var(--tile-size);
          border-radius: 999px;
          overflow: hidden;
          border: 1px solid rgba(248,236,210,.30);
          box-shadow: 0 4px 10px rgba(0,0,0,.4);
        }
        .partner-tile .avatar-wrap {
          border-color: rgba(212,99,62,.6);
        }
        .speaking .avatar-wrap {
          border-color: rgba(217,167,58,.8);
        }
        .name {
          font-family: var(--font-display);
          font-weight: 500;
          font-size: 13px;
          color: var(--card);
        }
        .role {
          font-family: var(--font-hand);
          font-size: 10px;
          letter-spacing: .1em;
          text-transform: uppercase;
          color: var(--gold-soft);
        }
        .role-spacer { height: 13px; }
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
        <p>Listen to the room — pick a Heartbreaker to talk to, move villas, or let the producers move the day.</p>
        <style jsx>{`
          .narration-empty {
            display: grid; place-items: center;
            padding: 8px 16px;
            color: var(--muted-on-dark);
            font-size: 13px;
            font-style: italic;
            border-top: 1px solid rgba(217,167,58,.18);
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
          padding: 10px 18px;
          background: linear-gradient(180deg, rgba(8,6,4,.65), rgba(8,6,4,.85));
          border-top: 1px solid rgba(217,167,58,.22);
          backdrop-filter: blur(6px);
          max-height: 26vh;
          overflow-y: auto;
          animation: drift-in 0.5s cubic-bezier(.22,.61,.36,1) both;
        }
        .narration-text {
          margin: 0 auto;
          max-width: 880px;
          color: var(--card);
          font-size: 15px;
          line-height: 1.5;
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
