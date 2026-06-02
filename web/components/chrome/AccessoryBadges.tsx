"use client";

import {
  Circle,
  CircleDot,
  Crown,
  Gem,
  Glasses,
  Sparkle,
  Sun,
  Watch,
  type LucideIcon,
} from "lucide-react";
import { findAccessory } from "../../lib/look";

// Map the catalog's icon-name strings to concrete lucide components. Keeping
// this lookup here (rather than importing by string) means the bundler can
// tree-shake unused icons and there is no dynamic-import cost at render.
const ICONS: Record<string, LucideIcon> = {
  Glasses,
  Circle,
  Gem,
  Watch,
  Crown,
  Sparkle,
  Sun,
  CircleDot,
};

type AccessoryBadgesProps = {
  /** Accessory ids from an HeartbreakerLook. */
  ids: string[];
  className?: string;
  /** Slightly smaller badges for compact / chip contexts. */
  compact?: boolean;
};

/**
 * A vertical rail of small icon badges, one per chosen accessory. Used on the
 * creator casting card (top-right) and reusable anywhere a look needs a quick
 * "what they're wearing" glance. Purely presentational; no runtime image work.
 */
export function AccessoryBadges({ ids, className, compact = false }: AccessoryBadgesProps) {
  const items = ids
    .map((id) => findAccessory(id))
    .filter((a): a is NonNullable<typeof a> => Boolean(a));

  if (items.length === 0) return null;

  return (
    <div
      className={`acc-badges${compact ? " is-compact" : ""}${className ? ` ${className}` : ""}`}
      role="list"
      aria-label="Accessories"
    >
      {items.map((a) => {
        const Icon = ICONS[a.icon] ?? Sparkle;
        return (
          <span className="acc-badge" role="listitem" key={a.id} title={`${a.label} · ${a.slot}`}>
            <Icon size={compact ? 13 : 16} strokeWidth={2.1} aria-hidden />
            <span className="sr-only">{a.label}</span>
          </span>
        );
      })}
      <style jsx>{`
        .acc-badges {
          display: flex;
          flex-direction: column;
          gap: 7px;
        }
        .acc-badge {
          display: inline-grid;
          place-items: center;
          width: 34px;
          height: 34px;
          border-radius: 50%;
          color: var(--card);
          background: rgba(8, 6, 4, .66);
          border: 1px solid rgba(217, 167, 58, .55);
          box-shadow: 0 4px 14px rgba(0, 0, 0, .42), inset 0 0 0 1px rgba(255, 244, 208, .12);
          backdrop-filter: blur(6px);
        }
        .is-compact .acc-badge {
          width: 26px;
          height: 26px;
          border-radius: 50%;
        }
        .sr-only {
          position: absolute;
          width: 1px;
          height: 1px;
          padding: 0;
          margin: -1px;
          overflow: hidden;
          clip: rect(0, 0, 0, 0);
          white-space: nowrap;
          border: 0;
        }
      `}</style>
    </div>
  );
}
