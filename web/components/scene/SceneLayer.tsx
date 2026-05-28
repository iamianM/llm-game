import type { ReactNode } from "react";

const LOCATION_TO_GRAD: Record<string, string> = {
  pool: "var(--grad-pool)",
  firepit: "var(--grad-firepit)",
  kitchen: "var(--grad-kitchen)",
  terrace: "var(--grad-terrace)",
  bedroom: "var(--grad-bedroom)",
  hideaway: "var(--grad-suite)",
  casa_pool: "var(--grad-casa)",
  casa_kitchen: "var(--grad-casa)",
  casa_terrace: "var(--grad-casa)",
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
  casa_terrace: "/images/locations/casa_terrace.webp",
};

export function SceneLayer({ location, children, onTap }: { location: string; children: ReactNode; onTap: () => void }) {
  const gradient = LOCATION_TO_GRAD[location] ?? "var(--grad-pool)";
  const image = LOCATION_TO_IMAGE[location];
  return (
    <section
      data-testid="scene-stage"
      className="scene-layer film-grain"
      onClick={onTap}
      style={{
        backgroundImage: image
          ? `linear-gradient(180deg, rgba(7,5,4,.02), rgba(7,5,4,.46)), url(${image}), ${gradient}`
          : gradient,
      }}
    >
      <div className="scene-vignette" aria-hidden />
      <div className="scene-warmth" aria-hidden />
      {children}
      <style jsx>{`
        .scene-layer {
          position: relative;
          width: 100%;
          height: 100%;
          overflow: hidden;
          isolation: isolate;
          background-position: center;
          background-size: cover;
          touch-action: manipulation;
        }
        .scene-vignette {
          position: absolute;
          inset: 0;
          z-index: 1;
          pointer-events: none;
          background:
            radial-gradient(120% 70% at 50% 0%, rgba(255,255,255,.14), transparent 40%),
            linear-gradient(180deg, rgba(0,0,0,.05), rgba(0,0,0,.12) 46%, rgba(0,0,0,.68));
        }
        .scene-warmth {
          position: absolute;
          inset: 0;
          z-index: 1;
          pointer-events: none;
          background: radial-gradient(45% 28% at 50% 18%, rgba(255,225,170,.18), transparent 68%);
          animation: ambient-pulse 8s ease-in-out infinite;
        }
      `}</style>
    </section>
  );
}
