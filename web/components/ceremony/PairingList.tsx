import type { CoupleSummary } from "../../lib/types";
import { Avatar } from "../ui/Avatar";

export function PairingList({ couples }: { couples: CoupleSummary[] }) {
  if (!couples.length) return null;
  return (
    <div className="pairing-list" data-testid="pairing-list">
      {couples.map((couple, idx) => (
        <div
          key={`${couple.partner_a_id}-${couple.partner_b_id}-${couple.formed_on_day}-${couple.formed_via}-${idx}`}
          className="pairing-row"
          style={{ animationDelay: `${Math.min(idx, 5) * 120 + 180}ms` }}
        >
          <div className="pairing-side">
            <Avatar id={couple.partner_a_id} name={couple.partner_a_name} size="sm" />
            <span className="pairing-name">{couple.partner_a_name}</span>
          </div>
          <span className="pairing-amp">&</span>
          <div className="pairing-side end">
            <span className="pairing-name">{couple.partner_b_name}</span>
            <Avatar id={couple.partner_b_id} name={couple.partner_b_name} size="sm" />
          </div>
        </div>
      ))}
      <style jsx>{`
        .pairing-list {
          display: grid;
          gap: 10px;
          margin: 0 auto;
          max-width: 480px;
        }
        .pairing-row {
          display: grid;
          grid-template-columns: 1fr auto 1fr;
          align-items: center;
          gap: 12px;
          padding: 10px 16px;
          border-radius: var(--r-pill);
          background: rgba(8,6,4,.55);
          border: 1px solid rgba(217,167,58,.35);
          color: var(--card);
          font-family: var(--font-display);
          font-size: 17px;
          opacity: 0;
          transform: translateY(8px);
          animation: pairing-in .6s cubic-bezier(.22,.61,.36,1) forwards;
        }
        @keyframes pairing-in {
          to { opacity: 1; transform: translateY(0); }
        }
        .pairing-side {
          display: inline-flex;
          align-items: center;
          gap: 10px;
        }
        .pairing-side.end { justify-content: flex-end; }
        .pairing-name {
          letter-spacing: .01em;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .pairing-amp {
          font-family: var(--font-hand);
          font-size: 26px;
          color: var(--gold);
          text-shadow: 0 0 12px var(--gold-glow);
        }
      `}</style>
    </div>
  );
}
