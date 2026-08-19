"use client";

import type { SessionState } from "../../lib/types";

export type AnsweredRoundView = {
  round_index: number;
  stem: string;
  chosen_label: string | null;
  correct_label: string | null;
  is_correct: boolean;
  points: number;
  reaction_line: string | null;
};

export type PendingChallengeView = {
  kind: string;
  finished?: boolean;
  round_index?: number;
  round_count?: number;
  stem?: string;
  trait_key?: string | null;
  tier?: number;
  mechanical?: boolean;
  target_id?: string | null;
  classification?: string | null;
  total_points?: number;
  audience_delta?: number;
  answered_rounds?: AnsweredRoundView[];
};

type Props = {
  state: SessionState;
  pendingChallenge: PendingChallengeView;
};

const CHALLENGE_THEME: Record<string, {
  title: string;
  kicker: string;
  mode: "quiz" | "pulse" | "detector" | "cards" | "finale";
}> = {
  compatibility_quiz: {
    title: "Compatibility Quiz",
    kicker: "Know your couple",
    mode: "quiz",
  },
  heart_rate: {
    title: "Pulse Race",
    kicker: "Monitors live",
    mode: "pulse",
  },
  couples_quiz: {
    title: "The Couples Quiz",
    kicker: "Private answers, public stakes",
    mode: "quiz",
  },
  lie_detector: {
    title: "Lie Detector",
    kicker: "The needle decides",
    mode: "detector",
  },
  kiss_wed_pass: {
    title: "Kiss Wed Pass",
    kicker: "Three cards, no hiding",
    mode: "cards",
  },
  final_couples: {
    title: "Final Couples",
    kicker: "One last public test",
    mode: "finale",
  },
};

const FINALE_FACETS = ["Knowledge", "Chemistry", "Honesty", "Banter", "Audacity"];
const CARD_LABELS = ["Kiss", "Wed", "Pass"];

export function ChallengeSpectacle({ state, pendingChallenge }: Props) {
  const theme = challengeTheme(pendingChallenge.kind);
  const currentRound = pendingChallenge.round_index ?? (pendingChallenge.round_count ?? 1) - 1;
  const roundCount = pendingChallenge.round_count ?? 1;
  const answered = pendingChallenge.answered_rounds ?? [];
  const correct = answered.filter((round) => round.is_correct).length;
  const progress = pendingChallenge.finished ? 100 : Math.max(0, Math.min(100, (currentRound / Math.max(1, roundCount)) * 100));

  return (
    <section className={`challenge-spectacle mode-${theme.mode}`} data-testid="challenge-spectacle">
      <div className="challenge-backdrop" aria-hidden />
      <header className="challenge-head">
        <p className="challenge-kicker">{theme.kicker}</p>
        <h2>{theme.title}</h2>
        <div className="challenge-progress" aria-label={`${currentRound + 1} of ${roundCount}`}>
          <span style={{ width: `${progress}%` }} />
        </div>
      </header>
      <div className="challenge-body">
        {theme.mode === "pulse" ? <PulseRaceCast state={state} round={currentRound} /> : null}
        {theme.mode === "detector" ? <DetectorFace round={currentRound} count={roundCount} finished={Boolean(pendingChallenge.finished)} /> : null}
        {theme.mode === "cards" ? <KissWedPassCards round={currentRound} finished={Boolean(pendingChallenge.finished)} /> : null}
        {theme.mode === "finale" ? <FinaleFacets round={currentRound} finished={Boolean(pendingChallenge.finished)} /> : null}
        {theme.mode === "quiz" ? <QuizBoard correct={correct} answered={answered.length} count={roundCount} /> : null}
      </div>
      <footer className="challenge-foot">
        <span>{pendingChallenge.finished ? "Result locked" : `Round ${Math.min(currentRound + 1, roundCount)} of ${roundCount}`}</span>
        {pendingChallenge.finished && pendingChallenge.classification ? <strong>{resultLabel(pendingChallenge.classification)}</strong> : null}
      </footer>
      <style jsx>{`
        .challenge-spectacle {
          position: relative;
          width: min(980px, calc(100% - 28px));
          min-height: min(45vh, 390px);
          align-self: center;
          justify-self: center;
          display: grid;
          grid-template-rows: auto 1fr auto;
          overflow: hidden;
          border: 1px solid rgba(217,167,58,.32);
          border-radius: var(--r-xl);
          background: linear-gradient(180deg, rgba(20,16,12,.64), rgba(8,6,4,.84));
          box-shadow: var(--shadow-stage), var(--inset-gold);
          color: var(--ink-on-dark);
          animation: challenge-pop .42s cubic-bezier(.22,.61,.36,1) both;
        }
        .challenge-backdrop {
          position: absolute;
          inset: 0;
          background:
            radial-gradient(70% 70% at 50% 0, rgba(217,167,58,.16), transparent 58%),
            linear-gradient(110deg, rgba(212,99,62,.15), transparent 34%, rgba(91,124,79,.14));
          opacity: .95;
          pointer-events: none;
        }
        .challenge-head, .challenge-body, .challenge-foot {
          position: relative;
          z-index: 1;
        }
        .challenge-head {
          display: grid;
          gap: 5px;
          justify-items: center;
          padding: 22px 24px 10px;
          text-align: center;
        }
        .challenge-kicker {
          margin: 0;
          font-family: var(--font-hand);
          color: var(--gold-soft);
          letter-spacing: .12em;
          text-transform: uppercase;
          font-size: 12px;
        }
        h2 {
          margin: 0;
          font-family: var(--font-display);
          font-size: clamp(32px, 5vw, 64px);
          font-weight: 650;
          line-height: .95;
          color: var(--card);
        }
        .challenge-progress {
          width: min(360px, 70vw);
          height: 6px;
          margin-top: 6px;
          border-radius: var(--r-pill);
          background: rgba(248,236,210,.12);
          overflow: hidden;
        }
        .challenge-progress span {
          display: block;
          height: 100%;
          border-radius: inherit;
          background: linear-gradient(90deg, var(--accent), var(--gold), var(--gold-soft));
          transition: width .45s cubic-bezier(.22,.61,.36,1);
          box-shadow: 0 0 18px var(--gold-glow);
        }
        .challenge-body {
          display: grid;
          place-items: center;
          padding: 10px 24px 16px;
        }
        .challenge-foot {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 10px;
          padding: 10px 18px 16px;
          color: var(--muted-on-dark);
          font-size: 13px;
        }
        .challenge-foot strong {
          color: var(--gold-soft);
          font-family: var(--font-display);
          font-size: 18px;
        }
        @keyframes challenge-pop {
          from { opacity: 0; transform: translateY(12px) scale(.985); }
          to { opacity: 1; transform: none; }
        }
        @media (max-width: 760px), (max-height: 720px) {
          .challenge-spectacle {
            width: calc(100% - 16px);
            min-height: 260px;
            border-radius: var(--r-lg);
          }
          .challenge-head { padding: 14px 16px 6px; }
          .challenge-body { padding: 6px 14px 10px; }
          h2 { font-size: clamp(26px, 8vw, 44px); }
        }
      `}</style>
    </section>
  );
}

function challengeTheme(kind: string) {
  const theme = CHALLENGE_THEME[kind];
  if (theme === undefined) {
    throw new Error(`Unsupported challenge kind: ${kind}`);
  }
  return theme;
}

function PulseRaceCast({ state, round }: { state: SessionState; round: number }) {
  const cast = state.heartbreakers.filter((heartbreaker) => !heartbreaker.eliminated).slice(0, 6);
  return (
    <div className="pulse-cast">
      {cast.map((heartbreaker, index) => {
        const value = 28 + ((heartbreaker.id.length * 13 + round * 17 + index * 9) % 62);
        return (
          <div className="pulse-row" key={heartbreaker.id}>
            <span>{heartbreaker.name}</span>
            <div><i style={{ width: `${value}%` }} /></div>
            <b>{value}</b>
          </div>
        );
      })}
      <style jsx>{`
        .pulse-cast {
          width: min(620px, 100%);
          display: grid;
          gap: 10px;
        }
        .pulse-row {
          display: grid;
          grid-template-columns: minmax(70px, 130px) 1fr 38px;
          align-items: center;
          gap: 12px;
        }
        .pulse-row span {
          font-family: var(--font-display);
          color: var(--card);
        }
        .pulse-row div {
          height: 12px;
          border-radius: var(--r-pill);
          background: rgba(248,236,210,.10);
          overflow: hidden;
        }
        .pulse-row i {
          display: block;
          height: 100%;
          border-radius: inherit;
          background: linear-gradient(90deg, var(--accent), var(--gold-soft));
          box-shadow: 0 0 18px rgba(212,99,62,.5);
          animation: monitor-beat 1.2s ease-in-out infinite;
        }
        .pulse-row b {
          color: var(--gold-soft);
          font-variant-numeric: tabular-nums;
        }
        @keyframes monitor-beat {
          0%, 100% { filter: brightness(1); }
          50% { filter: brightness(1.45); }
        }
      `}</style>
    </div>
  );
}

function DetectorFace({ round, count, finished }: { round: number; count: number; finished: boolean }) {
  const angle = finished ? 48 : -42 + (round / Math.max(1, count - 1)) * 84;
  return (
    <div className="detector">
      <div className="dial">
        <span className="mark left">Truth</span>
        <span className="mark right">Caught</span>
        <i style={{ transform: `rotate(${angle}deg)` }} />
      </div>
      <style jsx>{`
        .detector {
          width: min(420px, 100%);
          display: grid;
          place-items: center;
        }
        .dial {
          position: relative;
          width: min(360px, 78vw);
          aspect-ratio: 2 / 1;
          border-radius: 360px 360px 18px 18px;
          border: 1px solid rgba(217,167,58,.45);
          border-bottom: 0;
          background:
            radial-gradient(circle at 50% 100%, rgba(248,236,210,.16), transparent 40%),
            linear-gradient(90deg, rgba(91,124,79,.28), rgba(217,167,58,.16), rgba(193,75,58,.28));
          overflow: hidden;
        }
        .dial::after {
          content: "";
          position: absolute;
          left: 50%; bottom: 0;
          width: 22px; height: 22px;
          transform: translateX(-50%);
          border-radius: 50%;
          background: var(--gold-soft);
          box-shadow: 0 0 18px var(--gold-glow);
        }
        .dial i {
          position: absolute;
          left: 50%; bottom: 8px;
          width: 3px; height: 76%;
          transform-origin: 50% 100%;
          background: linear-gradient(180deg, #fff4ce, var(--accent));
          border-radius: 99px;
          transition: transform .55s cubic-bezier(.34,1.56,.64,1);
        }
        .mark {
          position: absolute;
          bottom: 18px;
          font-family: var(--font-hand);
          color: var(--gold-soft);
          font-size: 16px;
        }
        .left { left: 22px; }
        .right { right: 22px; }
      `}</style>
    </div>
  );
}

function KissWedPassCards({ round, finished }: { round: number; finished: boolean }) {
  return (
    <div className="kwp-cards">
      {CARD_LABELS.map((label, index) => (
        <div key={label} className={`kwp-card ${index === round && !finished ? "is-active" : ""} ${index < round || finished ? "is-used" : ""}`}>
          <span>{label}</span>
        </div>
      ))}
      <style jsx>{`
        .kwp-cards {
          display: flex;
          gap: clamp(10px, 3vw, 22px);
          perspective: 1000px;
        }
        .kwp-card {
          width: clamp(82px, 18vw, 138px);
          aspect-ratio: 3 / 4;
          display: grid;
          place-items: center;
          border-radius: var(--r-lg);
          border: 1px solid rgba(217,167,58,.45);
          background:
            linear-gradient(150deg, rgba(248,236,210,.18), transparent 36%),
            linear-gradient(180deg, rgba(42,30,20,.92), rgba(12,8,5,.95));
          box-shadow: 0 18px 38px -18px rgba(0,0,0,.8);
          transform: rotateY(-8deg);
          transition: transform .28s, box-shadow .28s, border-color .28s;
        }
        .kwp-card span {
          font-family: var(--font-display);
          font-size: clamp(22px, 4vw, 36px);
          color: var(--card);
        }
        .kwp-card.is-active {
          transform: translateY(-12px) rotateY(0);
          border-color: rgba(217,167,58,.9);
          box-shadow: 0 24px 48px -16px rgba(217,167,58,.55);
        }
        .kwp-card.is-used {
          opacity: .72;
        }
      `}</style>
    </div>
  );
}

function FinaleFacets({ round, finished }: { round: number; finished: boolean }) {
  return (
    <div className="facets">
      {FINALE_FACETS.map((facet, index) => (
        <div key={facet} className={`facet ${index === round && !finished ? "is-active" : ""} ${index < round || finished ? "is-lit" : ""}`}>
          <span>{index + 1}</span>
          <strong>{facet}</strong>
        </div>
      ))}
      <style jsx>{`
        .facets {
          display: grid;
          grid-template-columns: repeat(5, minmax(82px, 1fr));
          gap: 10px;
          width: min(760px, 100%);
        }
        .facet {
          min-height: 96px;
          display: grid;
          place-items: center;
          gap: 4px;
          padding: 12px 8px;
          border-radius: var(--r-lg);
          border: 1px solid rgba(248,236,210,.13);
          background: rgba(8,6,4,.42);
          color: var(--muted-on-dark);
          text-align: center;
          transition: transform .22s, border-color .22s, background .22s;
        }
        .facet span {
          display: grid;
          place-items: center;
          width: 28px; height: 28px;
          border-radius: 50%;
          background: rgba(217,167,58,.12);
          color: var(--gold-soft);
          font-family: var(--font-hand);
        }
        .facet strong {
          font-family: var(--font-display);
          font-size: 15px;
          color: inherit;
        }
        .facet.is-active, .facet.is-lit {
          border-color: rgba(217,167,58,.65);
          background: rgba(217,167,58,.14);
          color: var(--card);
        }
        .facet.is-active {
          transform: translateY(-8px);
          box-shadow: 0 18px 36px -22px var(--gold-glow);
        }
        @media (max-width: 720px) {
          .facets { grid-template-columns: repeat(2, minmax(0, 1fr)); }
          .facet { min-height: 56px; grid-template-columns: auto 1fr; text-align: left; }
        }
      `}</style>
    </div>
  );
}

function QuizBoard({ correct, answered, count }: { correct: number; answered: number; count: number }) {
  return (
    <div className="quiz-board">
      <div>
        <strong>{correct}</strong>
        <span>right</span>
      </div>
      <div>
        <strong>{answered}</strong>
        <span>answered</span>
      </div>
      <div>
        <strong>{count}</strong>
        <span>rounds</span>
      </div>
      <style jsx>{`
        .quiz-board {
          display: grid;
          grid-template-columns: repeat(3, minmax(84px, 1fr));
          gap: 12px;
          width: min(520px, 100%);
        }
        .quiz-board div {
          min-height: 104px;
          display: grid;
          place-items: center;
          align-content: center;
          gap: 4px;
          border-radius: var(--r-lg);
          border: 1px solid rgba(217,167,58,.28);
          background: rgba(8,6,4,.42);
        }
        strong {
          font-family: var(--font-display);
          font-size: clamp(34px, 6vw, 56px);
          color: var(--gold-soft);
          line-height: 1;
        }
        span {
          color: var(--muted-on-dark);
          text-transform: uppercase;
          font-size: 11px;
          letter-spacing: .12em;
        }
      `}</style>
    </div>
  );
}

function resultLabel(classification: string) {
  if (classification === "success") return "Crowd loved it";
  if (classification === "partial") return "Mixed reaction";
  return "Tough room";
}
