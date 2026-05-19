const LOCATION_TO_GRAD: Record<string, string> = {
  pool: "var(--grad-pool)",
  firepit: "var(--grad-firepit)",
  kitchen: "var(--grad-kitchen)",
  terrace: "var(--grad-terrace)",
  bedroom: "var(--grad-bedroom)",
  hideaway: "var(--grad-suite)",
  casa_pool: "var(--grad-casa)",
  casa_kitchen: "var(--grad-casa)",
  casa_terrace: "var(--grad-casa)"
};

const LOCATION_TO_IMAGE: Record<string, string> = {
  pool: "/images/locations/pool.webp",
  firepit: "/images/locations/firepit.webp",
  kitchen: "/images/locations/kitchen.webp",
  terrace: "/images/locations/terrace.webp",
  bedroom: "/images/locations/bedroom.webp",
  hideaway: "/images/locations/hideaway.webp",
  casa_pool: "/images/locations/casa_pool.webp",
  casa_kitchen: "/images/locations/casa_kitchen.webp",
  casa_terrace: "/images/locations/casa_terrace.webp"
};

export function VillaBackground({ location, children }: { location: string; children: React.ReactNode }) {
  const gradient = LOCATION_TO_GRAD[location] ?? "var(--grad-pool)";
  const image = LOCATION_TO_IMAGE[location];
  return (
    <section
      className="villa-bg film-grain"
      style={{
        backgroundImage: image
          ? `linear-gradient(180deg, rgba(7,5,4,.08), rgba(7,5,4,.62)), url(${image}), ${gradient}`
          : gradient,
        backgroundPosition: "center",
        backgroundSize: "cover"
      }}
    >
      <div className="villa-vignette" aria-hidden />
      <div className="villa-shine" aria-hidden />
      <div className="villa-stage">{children}</div>
      <style jsx>{`
        .villa-bg {
          position: relative;
          flex: 1 1 auto;
          min-height: 280px;
          display: flex;
          align-items: center;
          justify-content: center;
          overflow: hidden;
          isolation: isolate;
        }
        .villa-vignette {
          position: absolute; inset: 0;
          pointer-events: none;
          background:
            radial-gradient(120% 80% at 50% 0%, rgba(255,255,255,.14), transparent 35%),
            radial-gradient(140% 120% at 50% 100%, rgba(0,0,0,.55), transparent 60%);
          z-index: 1;
        }
        .villa-shine {
          position: absolute; inset: 0;
          pointer-events: none;
          z-index: 1;
          background: radial-gradient(45% 28% at 50% 18%, rgba(255,255,255,.16), transparent 65%);
          animation: ambient-pulse 8s ease-in-out infinite;
        }
        .villa-stage {
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
