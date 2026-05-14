const PALETTE = ["#b9502f", "#5b7c4f", "#c8932a", "#4a8fb8", "#8a5f78", "#7c654f"];

export function Avatar({ id, name, size = "md" }: { id: string; name: string; size?: "xs" | "sm" | "md" | "lg" | "xl" }) {
  const dims = { xs: 22, sm: 30, md: 44, lg: 80, xl: 210 }[size];
  const color = PALETTE[Math.abs(hash(id)) % PALETTE.length];
  return (
    <div
      className="grid shrink-0 place-items-center rounded-full border border-white/30 font-display font-bold text-[var(--card)] shadow-[var(--shadow-md)]"
      style={{ width: dims, height: dims, background: color, fontSize: Math.max(11, dims / 4) }}
      aria-label={name}
    >
      {initials(name)}
    </div>
  );
}

function initials(name: string) {
  if (name.toLowerCase() === "you") return "YO";
  return name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

function hash(value: string) {
  return [...value].reduce((acc, char) => acc + char.charCodeAt(0), 0);
}
