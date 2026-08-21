import type { DailyRecapView } from "../../lib/types";
import { Button } from "../ui/Button";

const SECTIONS = [
  { id: "your_day", label: "Your day" },
  { id: "while_busy", label: "While you were busy" },
] as const;

export function DayRecap({
  recap,
  onClose,
}: {
  recap: DailyRecapView;
  onClose: () => void;
}) {
  const recapItems = recap.items ?? [];
  return (
    <div
      data-screen="day-recap"
      className="fixed inset-0 z-30 grid place-items-center bg-[#1c1612]/85 p-4 backdrop-blur sm:p-8"
    >
      <section className="max-h-[calc(100dvh-2rem)] w-full max-w-2xl overflow-y-auto rounded-[var(--r-xl)] border border-gold bg-card p-5 text-ink shadow-[var(--shadow-stage)] sm:p-8">
        <p className="font-hand text-3xl text-accent">Daily Recap</p>
        <h2 className="mt-2 font-display text-3xl sm:text-4xl">
          Day {recap.day} at {recap.resort_label}
        </h2>
        <div className="mt-6 space-y-6">
          {SECTIONS.map((section) => {
            const items = recapItems.filter((item) => item.section === section.id);
            if (!items.length) return null;
            return (
              <section key={section.id} data-recap-section={section.id}>
                <h3 className="font-display text-lg text-accent">{section.label}</h3>
                <div className="mt-2 space-y-3">
                  {items.map((item, index) => (
                    <article
                      key={`${section.id}-${index}`}
                      data-recap-speaker={item.speaker_label}
                      data-recap-emphasis={item.emphasis}
                      className={
                        item.emphasis === "strong"
                          ? "rounded-[var(--r-md)] border border-gold bg-white/80 p-3"
                          : "rounded-[var(--r-md)] border border-line bg-white/60 p-3"
                      }
                    >
                      <p className="font-display text-xs uppercase tracking-[0.14em] text-accent">
                        {item.speaker_label}
                      </p>
                      <p className="mt-1 text-sm leading-6">{item.content}</p>
                    </article>
                  ))}
                </div>
              </section>
            );
          })}
          {!recapItems.length ? (
            <p className="rounded-[var(--r-md)] border border-line bg-white/60 p-3 text-sm leading-6">
              No major memories surfaced today.
            </p>
          ) : null}
        </div>
        <Button className="mt-7" onClick={onClose}>
          Continue
        </Button>
      </section>
    </div>
  );
}
