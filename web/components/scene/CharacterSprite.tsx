"use client";

import { motion, useReducedMotion } from "framer-motion";
import Image from "next/image";
import type { CSSProperties } from "react";
import type { Gender } from "../../lib/types";
import { findOutfit, findVibe, type IslanderLook } from "../../lib/look";
import { npcSprite } from "../../lib/scene/npc-art";
import { playerSprite } from "../../lib/scene/player-sprite";
import type { CharacterPose, Position } from "../../lib/scene/types";
import { AccessoryBadges } from "../chrome/AccessoryBadges";

type Props = {
  id: string;
  name: string;
  role: "player" | "npc";
  gender?: Gender;
  archetypeId?: string;
  look?: IslanderLook | null;
  position: Position;
  pose: CharacterPose;
  active: boolean;
  compact?: boolean;
  tappable?: boolean;
  onTap?: () => void;
};

export function CharacterSprite({ id, name, role, gender = "man", archetypeId = "heartthrob", look = null, position, pose, active, compact = false, tappable, onTap }: Props) {
  const reduce = useReducedMotion();
  if (position.hidden) return null;
  // The player's chosen look paints a soft outfit-accent aura behind the
  // standee plus a tidy rail of accessory badges, so the creator choices read
  // in-scene. When a baked per-outfit standee exists the clothes themselves
  // change; otherwise the aura carries the outfit color. NPCs never carry a look.
  const playerLook = role === "player" ? look : null;
  const src = role === "player" ? playerSprite(archetypeId, gender, playerLook?.outfit, playerLook?.characterId) : npcSprite(id);
  const sizeClass = role === "player" ? "is-player" : "is-npc";
  const outfit = playerLook ? findOutfit(playerLook.outfit) : null;
  const vibe = playerLook ? findVibe(playerLook.vibe) : null;
  const accessories = playerLook ? playerLook.accessories.slice(0, 4) : [];
  const style = {
    "--sprite-left": `${position.x}%`,
    "--sprite-top": `${position.y}%`,
    ...(outfit ? { "--look-accent": outfit.accent, "--look-primary": outfit.primary } : {}),
    ...(vibe ? { "--look-vibe": vibe.value } : {}),
  } as CSSProperties;
  // Inactive characters recede via lower light + a touch of depth-of-field
  // blur, NOT transparency: at the old 0.56 opacity a standee turned into a
  // translucent "ghost" over bright backgrounds (e.g. sunset water) — you
  // could see straight through the figure, which read as a broken render.
  const animate = {
    scale: position.scale,
    opacity: pose === "off_stage" ? 0 : position.dimmed ? 0.94 : 1,
    filter: active
      ? "saturate(1.08) brightness(1.05)"
      : position.dimmed
        ? "saturate(.66) brightness(.6) blur(1.4px)"
        : "saturate(.95)",
  };
  return (
    <div
      data-testid="character-sprite"
      data-character-id={id}
      data-role={role}
      data-position={role === "player" ? "bottom" : "stage"}
      data-pose={pose}
      data-tappable={tappable ? "true" : undefined}
      role={tappable ? "button" : undefined}
      tabIndex={tappable ? 0 : undefined}
      aria-label={tappable ? `Open options for ${name}` : undefined}
      onClick={tappable && onTap ? (e) => { e.stopPropagation(); onTap(); } : undefined}
      onKeyDown={tappable && onTap ? (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onTap(); }
      } : undefined}
      className={`character-sprite ${sizeClass} pose-${pose}${active ? " is-active" : ""}${position.dimmed ? " is-dimmed" : ""}${compact ? " is-compact" : ""}${tappable ? " is-tappable" : ""}`}
      style={style}
    >
      <motion.div
        className="character-motion"
        initial={reduce ? false : { opacity: 0, y: 18, scale: position.scale * 0.96 }}
        animate={animate}
        transition={reduce ? { duration: 0.06 } : { duration: active ? 0.36 : 0.28, ease: [0.22, 0.61, 0.36, 1] }}
      >
        {playerLook ? <div className="look-aura" aria-hidden /> : null}
        <div className="sprite-shadow" aria-hidden />
        <div className="sprite-image">
          {src ? (
            <Image src={src} alt="" fill sizes={role === "player" ? "360px" : "260px"} priority={role === "player"} />
          ) : (
            <span>{initials(name)}</span>
          )}
        </div>
        {accessories.length > 0 ? <AccessoryBadges ids={accessories} className="look-acc" compact /> : null}
        <div className="sprite-name">{name}</div>
      </motion.div>
      <style jsx global>{`
        .character-sprite {
          position: absolute;
          z-index: 3;
          left: var(--sprite-left);
          top: var(--sprite-top);
          transform: translate(-50%, calc(-100% + var(--lift, 0px)));
          transform-origin: 50% 100%;
          display: grid;
          justify-items: center;
          pointer-events: none;
          transition: transform .32s cubic-bezier(.22,.61,.36,1);
        }
        .character-sprite.is-tappable {
          pointer-events: auto;
          cursor: pointer;
        }
        .character-sprite.is-tappable:hover .sprite-image,
        .character-sprite.is-tappable:focus-visible .sprite-image {
          filter: drop-shadow(0 0 18px rgba(217,167,58,.55));
          transform: translateY(-2px);
          transition: filter .18s, transform .18s;
        }
        .character-sprite.is-tappable:focus-visible {
          outline: none;
        }
        .character-motion {
          position: relative;
          display: grid;
          justify-items: center;
          transform-origin: 50% 100%;
        }
        .sprite-shadow {
          position: absolute;
          left: 50%;
          bottom: 16px;
          width: 66%;
          height: 9%;
          transform: translateX(-50%);
          border-radius: 50%;
          background: rgba(0,0,0,.46);
          filter: blur(12px);
          z-index: 0;
        }
        .sprite-image {
          position: relative;
          z-index: 1;
          width: var(--sprite-width);
          height: var(--sprite-height);
          display: grid;
          place-items: center;
          color: var(--card);
          font-family: var(--font-display);
          font-size: 26px;
          text-shadow: 0 3px 10px rgba(0,0,0,.7);
        }
        .sprite-image :global(img) {
          object-fit: contain;
          object-position: 50% 100%;
          filter: drop-shadow(0 18px 20px rgba(0,0,0,.42));
        }
        .look-aura {
          position: absolute;
          left: 50%;
          bottom: 8%;
          width: 80%;
          height: 78%;
          transform: translateX(-50%);
          z-index: 0;
          pointer-events: none;
          border-radius: 50% 50% 44% 44%;
          background:
            radial-gradient(60% 70% at 50% 70%, color-mix(in srgb, var(--look-accent, #f4e3b8) 52%, transparent), transparent 72%),
            radial-gradient(80% 60% at 50% 24%, color-mix(in srgb, var(--look-vibe, #f2b441) 30%, transparent), transparent 70%);
          filter: blur(13px);
          opacity: .72;
        }
        .is-active .look-aura { opacity: .95; }
        .look-acc {
          position: absolute;
          z-index: 5;
          /* Hug the figure's right side at hip height (the standee is far
             narrower than its bounding box, so we bias well inward) instead of
             floating in the dead space beside it. Slight scale-down keeps the
             badges tasteful against a small in-scene figure. */
          top: 38%;
          right: 20%;
          transform: scale(0.84);
          transform-origin: top right;
          pointer-events: none;
          filter: drop-shadow(0 6px 14px rgba(0, 0, 0, .5));
        }
        .is-player {
          --sprite-width: clamp(220px, 28vw, 420px);
          --sprite-height: clamp(360px, 82vh, 720px);
          /* Always the foreground figure — above even an active NPC (z 6) so
             "you" never get occluded by whoever's speaking. */
          z-index: 7;
        }
        .is-npc {
          --sprite-width: clamp(180px, 23vw, 360px);
          --sprite-height: clamp(300px, 72vh, 620px);
        }
        .is-npc.is-active {
          z-index: 6;
        }
        .sprite-name {
          position: relative;
          z-index: 2;
          margin-top: -10px;
          padding: 3px 10px 5px;
          border-radius: var(--r-pill);
          background: rgba(8,6,4,.62);
          border: 1px solid rgba(217,167,58,.28);
          color: var(--ink-on-dark);
          font-family: var(--font-display);
          font-size: 14px;
          line-height: 1;
          text-shadow: 0 2px 8px rgba(0,0,0,.6);
          white-space: nowrap;
          max-width: min(150px, 28vw);
          overflow: hidden;
          text-overflow: ellipsis;
          opacity: 1;
          transition: opacity .18s ease;
        }
        .is-dimmed .sprite-name { opacity: 0; }
        .is-active .sprite-name { opacity: 1; }
        .is-player .sprite-name { display: none; }
        .pose-talking .sprite-image {
          animation: talking-sway 1.5s ease-in-out infinite;
        }
        .pose-reacting_good .sprite-image,
        .pose-reacting_bad .sprite-image {
          animation: reaction-pop .28s cubic-bezier(.34,1.56,.64,1);
        }
        @keyframes talking-sway {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-3px); }
        }
        @keyframes reaction-pop {
          from { transform: rotate(-2deg) scale(.98); }
          55% { transform: rotate(2deg) scale(1.04); }
          to { transform: none; }
        }
        /* When the choice fan is open the player tucks up + shrinks (mobile
           only) so the bottom option bars never cover the standee. On desktop
           the options are a centred column with room to spare, so "you" stay
           big and low at the far left. */
        .is-player.is-compact {
          --lift: 0px;
        }
        @media (max-width: 520px) {
          /* Love Island mobile framing: figures are big + close, cropping
             thigh-up so they fill the stage instead of floating small with a
             slab of dead sky overhead. The bottom-anchored standees have
             transparent headroom, so the box runs tall and the lower anchor
             (positions.ts) pushes the feet just under the frame. */
          .is-player {
            --sprite-width: clamp(250px, 68vw, 400px);
            --sprite-height: clamp(440px, 92vh, 700px);
          }
          .is-npc {
            --sprite-width: clamp(200px, 58vw, 340px);
            --sprite-height: clamp(380px, 80vh, 600px);
          }
          /* When the option cards open they overlay the lower body (faces still
             show), so the player only nudges slightly rather than flying up. */
          .is-player.is-compact {
            --lift: 0px;
          }
          .sprite-name {
            font-size: 12px;
            max-width: 120px;
          }
        }
      `}</style>
    </div>
  );
}

function initials(name: string) {
  return name.trim().split(" ").filter(Boolean).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}
