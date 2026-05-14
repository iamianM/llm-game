export function VillaMap({ snapshot }: { snapshot: Record<string, string[]> }) {
  return (
    <section className="rounded-[var(--r-md)] border border-white/10 bg-white/5 p-3">
      <h3 className="font-display text-lg">Where everyone is</h3>
      <div className="mt-3 space-y-2 text-sm">
        {Object.entries(snapshot).map(([location, names]) => (
          <div key={location} className="flex justify-between gap-3">
            <span className="text-[var(--muted-on-dark)]">{location}</span>
            <span className="text-right">{names.join(", ") || "empty"}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
