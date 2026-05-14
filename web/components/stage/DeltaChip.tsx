export function DeltaChip({ delta, reason }: { delta?: number | null; reason?: string | null }) {
  if (!delta || Math.abs(delta) < 1) return null;
  const positive = delta > 0;
  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${positive ? "bg-[var(--good-soft)] text-[#173225]" : "bg-[var(--bad-soft)] text-[#3b1614]"}`}
      title={reason ?? undefined}
    >
      Pulse {positive ? "+" : ""}
      {delta}
      {reason ? ` · ${reason}` : ""}
    </span>
  );
}
