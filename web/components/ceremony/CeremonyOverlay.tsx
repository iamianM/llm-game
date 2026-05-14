import type { CoupleSummary } from "../../lib/types";
import { Button } from "../ui/Button";
import { Narration } from "./Narration";
import { PairingList } from "./PairingList";

type Props = {
  title: string;
  narration: string;
  couples: CoupleSummary[];
  onContinue: () => void;
};

export function CeremonyOverlay({ title, narration, couples, onContinue }: Props) {
  return (
    <div data-screen="ceremony" className="fixed inset-0 z-30 grid place-items-center bg-[#1c1612]/90 p-8 backdrop-blur">
      <section className="max-w-3xl text-center">
        <p className="font-hand text-3xl text-gold">Paradise Calls</p>
        <h1 className="mt-2 font-display text-5xl text-[var(--card)]">{title}</h1>
        <Narration>{narration}</Narration>
        <PairingList couples={couples} />
        <Button className="mt-8" onClick={onContinue}>Continue</Button>
      </section>
    </div>
  );
}
