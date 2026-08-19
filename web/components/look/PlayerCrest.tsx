"use client";

import type { CSSProperties } from "react";
import { findHairColor, findSkinTone, findVibe, type HeartbreakerLook } from "../../lib/look";

/**
 * A deterministic, Vercel-safe "casting crest" for the player.
 *
 * The in-scene body is a prebaked photoreal standee that can only vary by
 * archetype+gender(+outfit), so skin tone and hair colour cannot repaint it
 * without an unbounded image matrix. This crest is the honest home for those
 * dials: a stylised portrait token (skin field + hair crown + vibe glow +
 * monogram) that *does* respond to every choice, and travels with the player
 * as their avatar across the HUD, profile, couples list and finale.
 *
 * Intentionally abstract — a premium emblem, not a cartoon face — so it sits
 * cleanly beside the photoreal NPC portraits instead of fighting them.
 */
type Size = "xs" | "sm" | "md" | "lg" | "xl" | "responsive";

const DIMS: Record<Exclude<Size, "responsive">, number> = { xs: 22, sm: 30, md: 44, lg: 80, xl: 168 };

export function PlayerCrest({ look, name, size = "md" }: { look: HeartbreakerLook; name: string; size?: Size }) {
  const skin = findSkinTone(look.skinTone).value;
  const hair = findHairColor(look.hairColor).value;
  const vibe = findVibe(look.vibe).value;
  const dims = size === "responsive" ? null : DIMS[size];
  const px = dims ?? 168;

  const style = {
    ...(dims
      ? { width: dims, height: dims }
      : { width: "var(--portrait-size, 168px)", height: "var(--portrait-size, 168px)" }),
    ["--crest-skin" as string]: skin,
    ["--crest-hair" as string]: hair,
    ["--crest-vibe" as string]: vibe,
    ["--crest-mono" as string]: dims ? `${Math.max(10, px / 3)}px` : "calc(var(--portrait-size, 168px) / 3)",
  } as CSSProperties;

  return (
    <div className="player-crest" style={style} aria-label={name} role="img">
      <span className="crest-face" aria-hidden />
      <span className="crest-hair" aria-hidden />
      <span className="crest-mono" aria-hidden>{initial(name)}</span>
      <span className="crest-ring" aria-hidden />
      <style jsx>{`
        .player-crest {
          position: relative;
          display: grid;
          place-items: center;
          border-radius: 50%;
          overflow: hidden;
          flex-shrink: 0;
          background: color-mix(in srgb, var(--crest-skin) 70%, #1a120c);
          box-shadow: var(--shadow-md);
        }
        /* Lit skin field — a soft key light up the right cheek. */
        .crest-face {
          position: absolute;
          inset: 0;
          z-index: 0;
          background:
            radial-gradient(72% 64% at 62% 70%, color-mix(in srgb, var(--crest-skin) 92%, #fff), var(--crest-skin) 70%),
            var(--crest-skin);
        }
        /* Hair crown — sits over the top with a curved hairline. */
        .crest-hair {
          position: absolute;
          left: -6%;
          right: -6%;
          top: -8%;
          height: 56%;
          z-index: 1;
          border-radius: 0 0 48% 48% / 0 0 76% 76%;
          background: linear-gradient(180deg, color-mix(in srgb, var(--crest-hair) 78%, #000) 4%, var(--crest-hair) 92%);
        }
        .crest-hair::after {
          content: "";
          position: absolute;
          left: 16%;
          top: 14%;
          width: 30%;
          height: 26%;
          border-radius: 50%;
          background: color-mix(in srgb, var(--crest-hair) 60%, #fff);
          opacity: .35;
          filter: blur(2px);
        }
        .crest-mono {
          position: relative;
          z-index: 2;
          margin-top: 28%;
          font-family: var(--font-display);
          font-style: italic;
          font-weight: 700;
          font-size: var(--crest-mono);
          line-height: 1;
          color: #fff7ec;
          text-shadow: 0 2px 6px rgba(0, 0, 0, .55);
          letter-spacing: -0.02em;
        }
        .crest-ring {
          position: absolute;
          inset: 0;
          z-index: 3;
          border-radius: 50%;
          pointer-events: none;
          box-shadow:
            inset 0 0 0 1px color-mix(in srgb, var(--crest-vibe) 60%, rgba(255, 244, 208, .5)),
            inset 0 0 12px color-mix(in srgb, var(--crest-vibe) 36%, transparent),
            0 0 0 1px rgba(8, 6, 4, .35);
        }
      `}</style>
    </div>
  );
}

function initial(name: string) {
  const trimmed = name.trim();
  if (!trimmed || trimmed.toLowerCase() === "you") return "Y";
  return trimmed[0].toUpperCase();
}
