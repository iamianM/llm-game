import type { IslanderSummary } from "../../lib/types";
import { Avatar } from "../ui/Avatar";

const moodTone: Record<string, { ring: string; glow: string; tag: string }> = {
  warm:    { ring: "rgba(244,227,184,.6)", glow: "rgba(217,167,58,.45)", tag: "Warm" },
  flirty:  { ring: "rgba(246,220,207,.85)", glow: "rgba(212,99,62,.55)", tag: "Flirty" },
  tense:   { ring: "rgba(247,226,221,.7)", glow: "rgba(193,75,58,.55)", tag: "Tense" },
  playful: { ring: "rgba(244,227,184,.85)", glow: "rgba(217,167,58,.55)", tag: "Playful" },
  defensive:{ ring: "rgba(164,189,151,.7)", glow: "rgba(91,124,79,.45)", tag: "Guarded" },
  content: { ring: "rgba(164,189,151,.7)", glow: "rgba(91,124,79,.45)", tag: "Content" },
  anxious: { ring: "rgba(181,161,135,.7)", glow: "rgba(120,106,88,.45)", tag: "Anxious" }
};

export function NpcPortrait({ npc }: { npc: IslanderSummary }) {
  const tone = moodTone[npc.mood] ?? { ring: "rgba(248,236,210,.4)", glow: "rgba(248,236,210,.2)", tag: npc.mood || "" };
  return (
    <div className="portrait">
      <div className="aureole" aria-hidden style={{ boxShadow: `0 0 60px ${tone.glow}` }} />
      <div className="frame" style={{ borderColor: tone.ring }}>
        <div className="inner-glow" />
        <div className="avatar-shell"><Avatar id={npc.id} name={npc.name} size="responsive" /></div>
      </div>
      <div className="nameplate">
        <span className="nameplate-name">{npc.name}</span>
        {tone.tag ? <span className="nameplate-mood">· {tone.tag}</span> : null}
      </div>

      <style jsx>{`
        .portrait {
          display: grid;
          place-items: center;
          gap: 12px;
          padding-top: 14px;
          animation: drift-up 0.5s cubic-bezier(.22,.61,.36,1) both;
          --portrait-size: clamp(120px, 18vh, 200px);
        }
        .aureole {
          position: absolute;
          width: calc(var(--portrait-size) + 36px);
          height: calc(var(--portrait-size) + 36px);
          border-radius: 50%;
          z-index: -1;
          animation: ambient-pulse 5s ease-in-out infinite;
        }
        .frame {
          position: relative;
          border-radius: 50%;
          border: 3px solid;
          padding: 5px;
          width: calc(var(--portrait-size) + 18px);
          height: calc(var(--portrait-size) + 18px);
          display: grid;
          place-items: center;
          background:
            radial-gradient(circle at 50% 30%, rgba(255,255,255,.08), transparent 60%),
            rgba(8,6,4,.4);
          box-shadow:
            inset 0 0 0 1px rgba(217,167,58,.18),
            inset 0 0 32px rgba(0,0,0,.6),
            0 12px 48px rgba(0,0,0,.55);
        }
        .inner-glow {
          position: absolute;
          inset: 5px;
          border-radius: 50%;
          pointer-events: none;
          background: radial-gradient(circle at 50% 30%, rgba(255,255,255,.16), transparent 55%);
          z-index: 1;
        }
        .frame :global(*) { z-index: 2; }
        .nameplate {
          display: inline-flex;
          align-items: baseline;
          gap: 8px;
          padding: 6px 18px;
          border-radius: var(--r-pill);
          background: rgba(8,6,4,.55);
          backdrop-filter: blur(6px);
          border: var(--frame-gold);
          font-family: var(--font-display);
          color: var(--ink-on-dark);
          letter-spacing: .02em;
        }
        .nameplate-name {
          font-size: 22px;
          font-weight: 600;
        }
        .nameplate-mood {
          font-size: 13px;
          color: var(--gold-soft);
          opacity: .85;
          font-style: italic;
          letter-spacing: .04em;
        }
      `}</style>
    </div>
  );
}
