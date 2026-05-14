import type { CoupleSummary } from "../../lib/types";
import { Avatar } from "../ui/Avatar";

export function PairingList({ couples }: { couples: CoupleSummary[] }) {
  if (!couples.length) return null;
  return (
    <div className="mt-8 grid gap-3">
      {couples.map((couple) => (
        <div
          key={`${couple.partner_a_id}-${couple.partner_b_id}`}
          className="mx-auto flex w-full max-w-md items-center justify-between rounded-[var(--r-lg)] border border-white/10 bg-white/10 p-3 text-[var(--card)]"
        >
          <div className="flex items-center gap-2">
            <Avatar id={couple.partner_a_id} name={couple.partner_a_name} size="sm" /> {couple.partner_a_name}
          </div>
          <span className="text-gold">&</span>
          <div className="flex items-center gap-2">
            {couple.partner_b_name}
            <Avatar id={couple.partner_b_id} name={couple.partner_b_name} size="sm" />
          </div>
        </div>
      ))}
    </div>
  );
}
