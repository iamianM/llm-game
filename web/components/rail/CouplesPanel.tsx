import type { CoupleSummary } from "../../lib/types";
import { Avatar } from "../ui/Avatar";

export function CouplesPanel({ couples }: { couples: CoupleSummary[] }) {
  return (
    <section className="rounded-[var(--r-md)] border border-white/10 bg-white/5 p-3">
      <h3 className="font-display text-lg">Couples</h3>
      <div className="mt-3 space-y-3">
        {couples.map((couple) => (
          <div key={`${couple.partner_a_id}-${couple.partner_b_id}`} className={`rounded border p-2 ${couple.is_player_couple ? "border-gold bg-[var(--gold-soft)]/10" : "border-white/10"}`}>
            <div className="flex items-center gap-2">
              <Avatar id={couple.partner_a_id} name={couple.partner_a_name} size="xs" />
              <span className="text-sm">{couple.partner_a_name} & {couple.partner_b_name}</span>
            </div>
            <p className="mt-1 text-xs text-[var(--muted-on-dark)]">Strength {couple.strength} - {couple.formed_via_label}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
