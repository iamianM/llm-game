const LOCATION_TO_GRAD: Record<string, string> = {
  pool: "var(--grad-pool)",
  flame_deck: "var(--grad-flame_deck)",
  kitchen: "var(--grad-kitchen)",
  terrace: "var(--grad-terrace)",
  bedroom: "var(--grad-bedroom)",
  private_suite: "var(--grad-suite)",
  flush_pool: "var(--grad-flush)",
  flush_kitchen: "var(--grad-flush)",
  flush_terrace: "var(--grad-flush)"
};

const LOCATION_TO_IMAGE: Record<string, string> = {
  pool: "/images/locations/pool.webp",
  flame_deck: "/images/locations/flame_deck.webp",
  kitchen: "/images/locations/kitchen.webp",
  terrace: "/images/locations/terrace.webp",
  bedroom: "/images/locations/bedroom.webp",
  private_suite: "/images/locations/private_suite.webp",
  flush_pool: "/images/locations/flush_pool.webp",
  flush_kitchen: "/images/locations/flush_kitchen.webp",
  flush_terrace: "/images/locations/flush_terrace.webp"
};

export function ResortBackground({ location, children }: { location: string; children: React.ReactNode }) {
  const gradient = LOCATION_TO_GRAD[location] ?? "var(--grad-pool)";
  const image = LOCATION_TO_IMAGE[location];
  return (
    <section
      className="resort-bg film-grain"
      style={{
        backgroundImage: image
          ? `linear-gradient(180deg, rgba(7,5,4,.08), rgba(7,5,4,.62)), url(${image}), ${gradient}`
          : gradient,
        backgroundPosition: "center",
        backgroundSize: "cover"
      }}
    >
      <div className="resort-vignette" aria-hidden />
      <div className="resort-shine" aria-hidden />
      <div className="resort-stage">{children}</div>
      <style jsx>{`
        .resort-bg {
          position: relative;
          flex: 1 1 auto;
          min-height: 280px;
          display: flex;
          align-items: center;
          justify-content: center;
          overflow: hidden;
          isolation: isolate;
        }
        .resort-vignette {
          position: absolute; inset: 0;
          pointer-events: none;
          background:
            radial-gradient(120% 80% at 50% 0%, rgba(255,255,255,.14), transparent 35%),
            radial-gradient(140% 120% at 50% 100%, rgba(0,0,0,.55), transparent 60%);
          z-index: 1;
        }
        .resort-shine {
          position: absolute; inset: 0;
          pointer-events: none;
          z-index: 1;
          background: radial-gradient(45% 28% at 50% 18%, rgba(255,255,255,.16), transparent 65%);
          animation: ambient-pulse 8s ease-in-out infinite;
        }
        .resort-stage {
          position: relative;
          z-index: 2;
          width: 100%;
          display: grid;
          place-items: center;
        }
      `}</style>
    </section>
  );
}
