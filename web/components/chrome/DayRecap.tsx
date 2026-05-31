import { Button } from "../ui/Button";

type Recap = { day?: unknown; items?: Array<{ content?: unknown; emotional_weight?: unknown }> };

export function DayRecap({
  recap,
  villaLabel = "Sunset Bay",
  onClose,
}: {
  recap: Recap;
  villaLabel?: string;
  onClose: () => void;
}) {
  const day = typeof recap.day === "number" ? recap.day : "?";
  const villa = villaLabel || "Sunset Bay";
  const items = Array.isArray(recap.items) ? recap.items : [];
  return (
    <div data-screen="day-recap" className="fixed inset-0 z-30 grid place-items-center bg-[#1c1612]/85 p-8 backdrop-blur">
      <section className="w-full max-w-2xl rounded-[var(--r-xl)] border border-gold bg-card p-8 text-ink shadow-[var(--shadow-stage)]">
        <p className="font-hand text-3xl text-accent">While you were busy</p>
        <h2 className="mt-2 font-display text-4xl">Day {day} at {villa}</h2>
        <div className="mt-6 space-y-3">
          {items.length ? (
            items.slice(0, 5).map((item, index) => (
              <p key={index} className="rounded-[var(--r-md)] border border-line bg-white/60 p-3 text-sm leading-6">
                {String(item.content ?? `A quiet shift moved through ${villa}.`)}
              </p>
            ))
          ) : (
            <p className="rounded-[var(--r-md)] border border-line bg-white/60 p-3 text-sm leading-6">No major whispers made it back to you.</p>
          )}
        </div>
        <Button className="mt-7" onClick={onClose}>Continue</Button>
      </section>
    </div>
  );
}
