import type { ReactNode } from "react";

const LOCATION_TO_GRAD: Record<string, string> = {
  pool: "var(--grad-pool)",
  flame_deck: "var(--grad-flame_deck)",
  kitchen: "var(--grad-kitchen)",
  terrace: "var(--grad-terrace)",
  bedroom: "var(--grad-bedroom)",
  private_suite: "var(--grad-suite)",
  flush_pool: "var(--grad-flush)",
  flush_kitchen: "var(--grad-flush)",
  flush_terrace: "var(--grad-flush)",
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
  flush_terrace: "/images/locations/flush_terrace.webp",
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
