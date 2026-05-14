import { Activity } from "lucide-react";

export function PulseMeter({ score, delta }: { score: number; delta?: number | null }) {
  const deltaText = delta ? `${delta > 0 ? "+" : ""}${delta}` : null;
  return (
    <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1 text-sm" aria-label={`Pulse score ${score}`}>
      <Activity size={14} className="text-gold" />
      <span>Pulse</span>
      <span className="font-semibold text-[var(--card)]">{score}</span>
      {deltaText ? <span className={delta && delta > 0 ? "text-[var(--good-soft)]" : "text-[var(--bad-soft)]"}>{deltaText}</span> : null}
    </div>
  );
}
