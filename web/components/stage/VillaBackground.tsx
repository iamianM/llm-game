export function VillaBackground({ location, children }: { location: string; children: React.ReactNode }) {
  return (
    <section className={`relative flex min-h-[300px] basis-[42vh] items-center justify-center overflow-hidden location-${location} film-grain`}>
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_20%,rgba(255,255,255,.24),transparent_28%)]" />
      <div className="relative z-10">{children}</div>
    </section>
  );
}
