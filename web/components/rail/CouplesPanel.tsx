import type { HeartbreakerLook } from "../../lib/look";
import type { CoupleSummary } from "../../lib/types";
import { Avatar } from "../ui/Avatar";

export function CouplesPanel({
  couples,
  playerId,
  playerLook = null,
}: {
  couples: CoupleSummary[];
  playerId?: string;
  playerLook?: HeartbreakerLook | null;
}) {
  const lookFor = (id: string) => (id === playerId ? playerLook : null);
  return (
    <section className="rail-section">
      <h3 className="rail-section-title">Couples</h3>
      <div className="couples">
        {couples.map((couple) => (
          <div
            key={`${couple.partner_a_id}-${couple.partner_b_id}`}
            className={`couple-row ${couple.is_player_couple ? "is-player" : ""}`}
          >
            <div className="couple-line">
              <Avatar id={couple.partner_a_id} name={couple.partner_a_name} size="xs" look={lookFor(couple.partner_a_id)} />
              <span className="couple-name">{couple.partner_a_name}</span>
              <span className="couple-amp">&</span>
              <span className="couple-name">{couple.partner_b_name}</span>
              <Avatar id={couple.partner_b_id} name={couple.partner_b_name} size="xs" look={lookFor(couple.partner_b_id)} />
            </div>
            <p className="couple-meta">
              <span>Strength <b>{couple.strength}</b></span>
              <span className="dot" aria-hidden>·</span>
              <span>{couple.formed_via_label}</span>
            </p>
          </div>
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
        .couples { display: grid; gap: 8px; }
        .couple-row {
          padding: 10px 12px;
          border-radius: var(--r-md);
          background: rgba(8,6,4,.5);
          border: 1px solid rgba(248,236,210,.08);
        }
        .couple-row.is-player {
          background: linear-gradient(180deg, rgba(217,167,58,.12), rgba(217,167,58,.04));
          border-color: rgba(217,167,58,.45);
        }
        .couple-line {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 12px;
          color: var(--ink-on-dark);
        }
        .couple-name { font-family: var(--font-display); font-size: 13.5px; }
        .couple-amp { color: var(--gold); font-family: var(--font-hand); font-size: 18px; }
        .couple-meta {
          margin: 6px 0 0;
          display: inline-flex;
          gap: 6px;
          font-size: 11px;
          color: var(--muted-on-dark);
          letter-spacing: .03em;
        }
        .couple-meta b { color: var(--card); font-variant-numeric: tabular-nums; }
        .couple-meta .dot { opacity: .55; }
      `}</style>
    </section>
  );
}
