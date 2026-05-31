import { Button } from "../ui/Button";

type RecapItem = { content?: unknown; holder_id?: unknown; emotional_weight?: unknown };
type Recap = { day?: unknown; items?: Array<RecapItem> };

export function DayRecap({
  recap,
  villaLabel = "Sunset Bay",
  speakers = {},
  playerId = "player",
  onClose,
}: {
  recap: Recap;
  villaLabel?: string;
  // holder_id -> display name, so each whisper is attributed to whoever it
  // belongs to. Recap memories are first-person ("I noticed...", "I remember
  // you..."), and the recap blends the player's own takeaways with islander
  // whispers — without a speaker label the reader can't tell whose "I" each
  // card is. The player's own id maps to "You".
  speakers?: Record<string, string>;
  playerId?: string;
  onClose: () => void;
}) {
  const day = typeof recap.day === "number" ? recap.day : "?";
  const villa = villaLabel || "Sunset Bay";
  const items = Array.isArray(recap.items) ? recap.items : [];
  const speakerFor = (holder: unknown): string => {
    if (typeof holder !== "string" || !holder) return "Someone";
    if (holder === playerId) return "You";
    return speakers[holder] || "Someone";
  };
  return (
    <div data-screen="day-recap" className="fixed inset-0 z-30 grid place-items-center bg-[#1c1612]/85 p-8 backdrop-blur">
      <section className="w-full max-w-2xl rounded-[var(--r-xl)] border border-gold bg-card p-8 text-ink shadow-[var(--shadow-stage)]">
        <p className="font-hand text-3xl text-accent">While you were busy</p>
        <h2 className="mt-2 font-display text-4xl">Day {day} at {villa}</h2>
        <div className="mt-6 space-y-3">
          {items.length ? (
            items.slice(0, 5).map((item, index) => {
              const speaker = speakerFor(item.holder_id);
              return (
                <div
                  key={index}
                  data-recap-speaker={speaker}
                  className="rounded-[var(--r-md)] border border-line bg-white/60 p-3"
                >
                  <p className="font-display text-xs uppercase tracking-[0.14em] text-accent">{speaker}</p>
                  <p className="mt-1 text-sm leading-6">
                    {String(item.content ?? `A quiet shift moved through ${villa}.`)}
                  </p>
                </div>
              );
            })
          ) : (
            <p className="rounded-[var(--r-md)] border border-line bg-white/60 p-3 text-sm leading-6">No major whispers made it back to you.</p>
          )}
        </div>
        <Button className="mt-7" onClick={onClose}>Continue</Button>
      </section>
    </div>
  );
}
