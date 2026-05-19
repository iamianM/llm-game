import type { IslanderSummary } from "../../lib/types";
import { Avatar } from "../ui/Avatar";

export function CastGrid({ cast, onOpenProfile }: { cast: IslanderSummary[]; onOpenProfile: (npcId: string) => void }) {
  return (
    <section className="rail-section">
      <h3 className="rail-section-title">Heartbreakers</h3>
      <div className="cast-grid">
        {cast.map((npc) => (
          <button
            key={npc.id}
            aria-label={`Open ${npc.name} profile`}
            onClick={() => onOpenProfile(npc.id)}
            className={`cast-tile mood-${npc.mood ?? "neutral"}`}
          >
            <Avatar id={npc.id} name={npc.name} size="sm" />
            <span className="cast-name">{npc.name}</span>
            {npc.eliminated ? <span className="cast-eliminated">Heart Out</span> : null}
          </button>
        ))}
      </div>
      <style jsx>{`
        .rail-section {
          padding: 14px 14px 16px;
          border-radius: var(--r-lg);
          background: rgba(248,236,210,.04);
          border: 1px solid rgba(248,236,210,.08);
        }
        .rail-section-title {
          margin: 0 0 12px;
          font-size: 10px;
          letter-spacing: .16em;
          text-transform: uppercase;
          font-weight: 700;
          color: var(--gold-soft);
        }
        .cast-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 8px;
        }
        .cast-tile {
          display: grid;
          place-items: center;
          gap: 6px;
          padding: 10px 4px;
          border-radius: var(--r-md);
          background: rgba(8,6,4,.4);
          border: 1px solid rgba(248,236,210,.08);
          cursor: pointer;
          transition: transform .15s, border-color .15s, background .15s;
        }
        .cast-tile:hover {
          transform: translateY(-2px);
          background: rgba(217,167,58,.06);
          border-color: rgba(217,167,58,.35);
        }
        .cast-name {
          font-size: 11px;
          color: var(--ink-on-dark);
          letter-spacing: .04em;
        }
        .cast-eliminated {
          font-size: 9px;
          color: var(--bad-soft);
          opacity: .85;
          text-transform: uppercase;
          letter-spacing: .12em;
        }
      `}</style>
    </section>
  );
}
