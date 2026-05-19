"use client";

import Image from "next/image";

const VIBE: Record<string, { gradient: string; accentColor: string; tag: string; image: string }> = {
  heartthrob: {
    gradient: "linear-gradient(160deg, #d8786c 0%, #b9502f 55%, #5a2114 100%)",
    accentColor: "#ffb39e",
    tag: "Charisma forward - Risk: high",
    image: "/images/archetypes/heartthrob.webp"
  },
  class_clown: {
    gradient: "linear-gradient(160deg, #e6c46e 0%, #b6862b 55%, #5a3f12 100%)",
    accentColor: "#ffe2a3",
    tag: "Crowd magnet - Risk: medium",
    image: "/images/archetypes/class_clown.webp"
  },
  loyal_friend: {
    gradient: "linear-gradient(160deg, #8fb084 0%, #5b7c4f 55%, #233319 100%)",
    accentColor: "#c1d8b3",
    tag: "Steady ground - Risk: low",
    image: "/images/archetypes/loyal_friend.webp"
  }
};

type Props = {
  id: string;
  title: string;
  bonus: string;
  advantage: string;
  selected: boolean;
  onSelect: () => void;
};

export function ArchetypeCard({ id, title, bonus, advantage, selected, onSelect }: Props) {
  const vibe = VIBE[id] ?? VIBE.heartthrob;
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className={`archetype-card ${selected ? "is-selected" : ""}`}
      style={{ ["--vibe-gradient" as never]: vibe.gradient, ["--vibe-accent" as never]: vibe.accentColor }}
    >
      <div className="card-hero" aria-hidden>
        <Image
          className="hero-image"
          src={vibe.image}
          alt=""
          fill
          sizes="(max-width: 760px) 94vw, 31vw"
          style={{ objectFit: "cover", objectPosition: "50% 45%" }}
        />
        <div className="hero-glow" />
        <div className="hero-tag">{vibe.tag}</div>
      </div>
      <div className="card-body">
        <h2 className="card-title">{title}</h2>
        <div className="card-bonus">{bonus}</div>
        <p className="card-blurb">{advantage}</p>
        <div className="card-status">
          <span className="card-status-dot" />
          {selected ? "Selected" : "Tap to pick"}
        </div>
      </div>
      <style jsx>{`
        .archetype-card {
          position: relative;
          display: grid;
          grid-template-rows: minmax(120px, 22vh) 1fr;
          border-radius: var(--r-xl);
          border: 1px solid rgba(248,236,210,.12);
          background: rgba(20,16,12,.7);
          color: var(--ink-on-dark);
          overflow: hidden;
          cursor: pointer;
          text-align: left;
          transition: transform .25s cubic-bezier(.22,.61,.36,1), box-shadow .25s, border-color .25s;
          box-shadow: var(--shadow-md);
          backdrop-filter: blur(8px);
        }
        .archetype-card:hover {
          transform: translateY(-4px);
          box-shadow: var(--shadow-lg);
          border-color: rgba(217,167,58,.4);
        }
        .archetype-card.is-selected {
          transform: translateY(-6px);
          border-color: rgba(217,167,58,.85);
          box-shadow: var(--shadow-lg), 0 0 0 2px rgba(217,167,58,.45), 0 0 32px var(--vibe-accent);
        }

        .card-hero {
          position: relative;
          background: var(--vibe-gradient);
          overflow: hidden;
          border-bottom: var(--frame-gold);
        }
        .hero-image {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
        }
        .hero-glow {
          position: absolute;
          inset: 0;
          background:
            radial-gradient(70% 70% at 30% 30%, rgba(255,235,200,.18), transparent 50%),
            linear-gradient(180deg, transparent 45%, rgba(0,0,0,.62) 100%),
            radial-gradient(60% 60% at 80% 80%, rgba(0,0,0,.25), transparent 60%);
          opacity: .9;
        }
        .hero-tag {
          position: absolute;
          left: 14px; bottom: 12px;
          font-family: var(--font-hand);
          font-size: 15px;
          letter-spacing: .04em;
          color: var(--vibe-accent);
          opacity: .95;
        }

        .card-body {
          padding: 14px 16px 16px;
          display: grid;
          gap: 6px;
        }
        .card-title {
          font-family: var(--font-display);
          font-size: 22px;
          font-weight: 600;
          margin: 0;
        }
        .card-bonus {
          display: inline-block;
          align-self: start;
          padding: 3px 10px;
          border-radius: var(--r-pill);
          font-size: 11px;
          font-weight: 700;
          letter-spacing: .08em;
          text-transform: uppercase;
          background: rgba(217,167,58,.12);
          border: 1px solid rgba(217,167,58,.35);
          color: var(--gold-soft);
        }
        .card-blurb {
          font-size: 12.5px;
          line-height: 1.45;
          color: var(--muted-on-dark);
          margin: 4px 0 8px;
        }
        .card-status {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          letter-spacing: .12em;
          text-transform: uppercase;
          color: var(--muted-on-dark);
        }
        .card-status-dot {
          width: 8px; height: 8px;
          border-radius: 50%;
          background: var(--muted-on-dark);
          transition: background .2s, box-shadow .2s;
        }
        .archetype-card.is-selected .card-status {
          color: var(--gold-soft);
        }
        .archetype-card.is-selected .card-status-dot {
          background: var(--gold);
          box-shadow: 0 0 12px var(--gold-glow);
        }
        @media (max-width: 760px) {
          .archetype-card {
            grid-template-rows: 118px auto;
          }
        }
      `}</style>
    </button>
  );
}
