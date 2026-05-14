"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { newSession } from "../../lib/api";
import type { Gender } from "../../lib/types";
import { ArchetypeCard } from "../../components/chrome/ArchetypeCard";
import { Button } from "../../components/ui/Button";

const ARCHETYPES = [
  { id: "heartthrob", title: "Heartthrob", bonus: "+3 Charm", advantage: "Walk into Sunset Bay with instant spark and a little extra first-impression heat." },
  { id: "class_clown", title: "Class Clown", bonus: "+3 Banter", advantage: "Win the room with quick jokes, warm timing, and a crowd-pleaser edge." },
  { id: "loyal_friend", title: "Loyal Friend", bonus: "+3 Loyalty", advantage: "Start with steadier bonds and a reputation for meaning what you say." }
];

export default function NewRunPage() {
  const [archetype, setArchetype] = useState("heartthrob");
  const [gender, setGender] = useState<Gender>("man");
  const [mockLlm, setMockLlm] = useState(false);
  const router = useRouter();
  const mutation = useMutation({
    mutationFn: () => newSession(archetype, gender, mockLlm),
    onSuccess: (data) => {
      localStorage.setItem("paradise.currentSessionId", data.session_id);
      router.push(`/play/${data.session_id}`);
    }
  });

  return (
    <main className="min-h-screen bg-bg px-8 py-10 text-[var(--card)]">
      <div className="mx-auto max-w-6xl">
        <p className="text-sm text-[var(--muted-on-dark)]">Paradise Hearts casting</p>
        <h1 className="mt-2 font-display text-5xl">Choose your opening vibe</h1>
        <div className="mt-8 grid grid-cols-3 gap-5">
          {ARCHETYPES.map((item) => (
            <ArchetypeCard key={item.id} {...item} selected={archetype === item.id} onSelect={() => setArchetype(item.id)} />
          ))}
        </div>
        <section className="mt-8 rounded-[var(--r-lg)] border border-white/10 bg-white/5 p-5">
          <h2 className="font-display text-2xl">Heartbreaker card</h2>
          <p className="mt-2 text-sm text-[var(--muted-on-dark)]">Stats are assigned from your archetype for this MVP.</p>
          <div className="mt-4 flex gap-3">
            <Button variant={gender === "man" ? "primary" : "secondary"} onClick={() => setGender("man")}>Man</Button>
            <Button variant={gender === "woman" ? "primary" : "secondary"} onClick={() => setGender("woman")}>Woman</Button>
          </div>
        </section>
        <section className="mt-5 rounded-[var(--r-lg)] border border-white/10 bg-white/5 p-5">
          <h2 className="font-display text-2xl">Story engine</h2>
          <p className="mt-2 text-sm text-[var(--muted-on-dark)]">Use test mode for fast deterministic checks, or real mode for authored live dialogue.</p>
          <div className="mt-4 flex gap-3">
            <Button variant={mockLlm ? "primary" : "secondary"} onClick={() => setMockLlm(true)}>Test mode</Button>
            <Button variant={!mockLlm ? "primary" : "secondary"} onClick={() => setMockLlm(false)}>Real mode</Button>
          </div>
        </section>
        <Button disabled={mutation.isPending} onClick={() => mutation.mutate()} className="mt-8">
          {mutation.isPending ? "Opening Sunset Bay..." : "Enter Sunset Bay"}
        </Button>
        {mutation.error ? <p className="mt-4 text-[var(--bad-soft)]">{mutation.error.message}</p> : null}
      </div>
    </main>
  );
}
