"use client";

import { motion, useReducedMotion } from "framer-motion";
import Image from "next/image";
import type { CSSProperties } from "react";
import type { Gender } from "../../lib/types";
import { playerSprite } from "../../lib/scene/player-sprite";
import type { CharacterPose, Position } from "../../lib/scene/types";

const NPC_IMAGE_BY_ID: Record<string, string> = {
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

type Props = {
  id: string;
  name: string;
  role: "player" | "npc";
  gender?: Gender;
  archetypeId?: string;
  position: Position;
  pose: CharacterPose;
  active: boolean;
};

export function CharacterSprite({ id, name, role, gender = "man", archetypeId = "heartthrob", position, pose, active }: Props) {
  const reduce = useReducedMotion();
  if (position.hidden) return null;
  const src = role === "player" ? playerSprite(archetypeId, gender) : NPC_IMAGE_BY_ID[id];
  const sizeClass = role === "player" ? "is-player" : "is-npc";
  const style = {
    "--sprite-left": `${position.x}%`,
    "--sprite-top": `${position.y}%`,
  } as CSSProperties;
  const animate = {
    scale: position.scale,
    opacity: pose === "off_stage" ? 0 : position.dimmed ? 0.56 : 1,
    filter: active ? "saturate(1.08) brightness(1.05)" : position.dimmed ? "saturate(.72) brightness(.82)" : "saturate(.95)",
  };
  return (
    <div
      data-testid="character-sprite"
      data-character-id={id}
      data-role={role}
      data-position={role === "player" ? "bottom" : "stage"}
      data-pose={pose}
      className={`character-sprite ${sizeClass} pose-${pose}${active ? " is-active" : ""}`}
      style={style}
    >
      <motion.div
        className="character-motion"
        initial={reduce ? false : { opacity: 0, y: 18, scale: position.scale * 0.96 }}
        animate={animate}
        transition={reduce ? { duration: 0.06 } : { duration: active ? 0.36 : 0.28, ease: [0.22, 0.61, 0.36, 1] }}
      >
        <div className="sprite-shadow" aria-hidden />
        <div className="sprite-image">
          {src ? (
            <Image src={src} alt="" fill sizes={role === "player" ? "360px" : "260px"} priority={role === "player"} />
          ) : (
            <span>{initials(name)}</span>
          )}
        </div>
        <div className="sprite-name">{name}</div>
      </motion.div>
      <style jsx global>{`
        .character-sprite {
          position: absolute;
          z-index: 3;
          left: var(--sprite-left);
          top: var(--sprite-top);
          transform: translate(-50%, -100%);
          transform-origin: 50% 100%;
          display: grid;
          justify-items: center;
          pointer-events: none;
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
        .is-player {
          --sprite-width: clamp(120px, 22vw, 220px);
          --sprite-height: clamp(170px, 28vh, 320px);
          z-index: 4;
        }
        .is-npc {
          --sprite-width: clamp(96px, 17vw, 200px);
          --sprite-height: clamp(150px, 27vh, 320px);
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
          opacity: 0;
          transition: opacity .18s ease;
        }
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
        @media (max-width: 520px) {
          .is-player {
            --sprite-width: clamp(108px, 32vw, 160px);
            --sprite-height: clamp(152px, 26vh, 240px);
          }
          .is-npc {
            --sprite-width: clamp(78px, 22vw, 138px);
            --sprite-height: clamp(124px, 25vh, 220px);
          }
          .sprite-name {
            font-size: 12px;
            max-width: 100px;
          }
        }
      `}</style>
    </div>
  );
}

function initials(name: string) {
  return name.trim().split(" ").filter(Boolean).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}
