"use client";

import Image from "next/image";
import { findOutfit, findVibe, type HeartbreakerLook } from "../../lib/look";
import { isRosterId } from "../../lib/roster";
import { hasOutfitStandee, playerSprite } from "../../lib/scene/player-sprite";

/**
 * The avatar "casting card" stage. Renders the prebaked photoreal standee for
 * the chosen archetype+gender and grades it with the selected outfit palette
 * (a soft duotone wash + accent ring + glow) so wardrobe/energy choices read
 * visibly without any runtime image generation. Vercel-safe.
 *
 * Shared by the casting card and the Sunset Bay wardrobe modal so the
 * preview is pixel-identical in both places.
 */
export function LookStage({ look, compact = false }: { look: HeartbreakerLook; compact?: boolean }) {
  const outfit = findOutfit(look.outfit);
  const vibe = findVibe(look.vibe);
  const src = playerSprite(look.archetype, look.gender, look.outfit, look.characterId);
  // When the standee already wears its real outfit — a baked outfit variant, or
  // a roster pick whose single standee is its own look — drop the duotone wash
  // so the garment color reads true; keep it as a stylistic grade otherwise.
  const realOutfit = isRosterId(look.characterId) || hasOutfitStandee(look.archetype, look.gender, look.outfit);
  return (
    <div
      className={`look-stage${compact ? " is-compact" : ""}${realOutfit ? " has-real-outfit" : ""}`}
      style={
        {
          ["--ot-primary" as string]: outfit.primary,
          ["--ot-secondary" as string]: outfit.secondary,
          ["--ot-accent" as string]: outfit.accent,
          ["--vibe" as string]: vibe.value,
        } as React.CSSProperties
      }
    >
      <span className="stage-glow" aria-hidden />
      <span className="stage-arch" aria-hidden />
      <div className="sprite-wrap">
        <Image src={src} alt="" fill sizes={compact ? "120px" : "(max-width: 760px) 70vw, 460px"} priority={!compact} style={{ objectFit: "contain", objectPosition: "50% 100%" }} />
        <span className="sprite-tint" aria-hidden />
      </div>
      <span className="floor-shadow" aria-hidden />
      {!compact ? (
        <>
          <span className="sparkle s-a" aria-hidden />
          <span className="sparkle s-b" aria-hidden />
        </>
      ) : null}
      <style jsx>{`
        .look-stage {
          position: absolute;
          inset: 0;
          overflow: hidden;
          display: grid;
          place-items: center;
          background:
            radial-gradient(82% 56% at 50% 14%, color-mix(in srgb, var(--ot-accent) 42%, transparent), transparent 56%),
            radial-gradient(86% 84% at 50% 60%, var(--ot-primary), color-mix(in srgb, var(--ot-primary) 40%, #050302) 64%, #050302 100%);
        }
        .stage-glow {
          position: absolute;
          inset: 10% 16% auto;
          height: 42%;
          border-radius: 999px;
          background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--vibe) 50%, var(--ot-accent)), transparent);
          filter: blur(10px);
        }
        .stage-arch {
          position: absolute;
          inset: 12% 9% 18%;
          border-radius: 30px 30px 12px 12px;
          border: 1px solid color-mix(in srgb, var(--ot-accent) 30%, transparent);
          background: linear-gradient(90deg, rgba(255, 244, 208, .06), transparent 32%, rgba(255, 244, 208, .07) 60%, transparent);
        }
        .sprite-wrap {
          position: absolute;
          left: 50%;
          bottom: 0;
          transform: translateX(-50%);
          width: min(104%, 460px);
          height: 96%;
          z-index: 2;
          filter: drop-shadow(0 22px 24px rgba(0, 0, 0, .44));
        }
        .is-compact .sprite-wrap { width: 100%; height: 100%; }
        .sprite-tint {
          position: absolute;
          inset: 0;
          z-index: 1;
          pointer-events: none;
          background: linear-gradient(180deg, transparent 38%, color-mix(in srgb, var(--ot-secondary) 55%, transparent) 78%, color-mix(in srgb, var(--ot-primary) 70%, transparent));
          mix-blend-mode: soft-light;
          opacity: .9;
        }
        .has-real-outfit .sprite-tint { opacity: .22; }
        .floor-shadow {
          position: absolute;
          left: 24%;
          right: 24%;
          bottom: 5%;
          height: 4%;
          z-index: 1;
          border-radius: 50%;
          background: radial-gradient(ellipse, rgba(0, 0, 0, .5), transparent 70%);
        }
        .sparkle {
          position: absolute;
          z-index: 3;
          width: 6px;
          height: 6px;
          border-radius: 999px;
          background: var(--vibe);
          box-shadow: 0 0 10px var(--vibe);
          opacity: .9;
        }
        .s-a { left: 17%; top: 19%; }
        .s-b { right: 18%; top: 26%; width: 4px; height: 4px; }
      `}</style>
    </div>
  );
}
