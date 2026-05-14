import clsx from "clsx";

export function Pill({ children, tone = "default" }: { children: React.ReactNode; tone?: "default" | "accent" | "good" | "bad" | "gold" }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold",
        tone === "default" && "border-line bg-[var(--card-alt)] text-[var(--muted)]",
        tone === "accent" && "border-accent bg-[var(--accent-soft)] text-accent",
        tone === "good" && "border-sage bg-[#e7f0df] text-sage",
        tone === "bad" && "border-bad bg-[var(--bad-soft)] text-bad",
        tone === "gold" && "border-gold bg-[var(--gold-soft)] text-[#775111]"
      )}
    >
      {children}
    </span>
  );
}
