"use client";

import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { getCast } from "../../lib/api";
import { Avatar } from "../ui/Avatar";

export function CastPopout({ sessionId, npcId, onClose }: { sessionId: string; npcId: string; onClose: () => void }) {
  const { data } = useQuery({ queryKey: ["cast", sessionId, npcId], queryFn: () => getCast(sessionId, npcId) });
  const closeRef = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="relative z-50">
      <button className="fixed inset-0 bg-black/60 backdrop-blur" aria-label="Close profile" onClick={onClose} />
      <div role="dialog" aria-modal="true" aria-labelledby="cast-title" className="fixed inset-0 grid place-items-center p-6">
        <section className="max-h-[80vh] w-full max-w-xl overflow-y-auto rounded-[var(--r-lg)] bg-card p-6 text-ink shadow-[var(--shadow-lg)]">
          {data ? (
            <>
              <div className="flex items-center gap-4">
                <Avatar id={data.id} name={data.name} size="lg" />
                <div>
                  <h2 id="cast-title" className="font-display text-3xl text-accent">{data.name}</h2>
                  <p className="text-sm text-[var(--muted)]">{data.archetype} - {data.location}</p>
                </div>
              </div>
              <p className="mt-5 leading-7">{data.backstory}</p>
              <h3 className="mt-5 font-display text-xl">Relationship</h3>
              {Object.entries(data.relationship).map(([key, value]) => (
                <div key={key} className="mt-2">
                  <div className="flex justify-between text-sm"><span>{key}</span><span>{value}</span></div>
                  <div className="h-2 rounded bg-[var(--line)]"><div className="h-2 rounded bg-accent" style={{ width: `${value}%` }} /></div>
                </div>
              ))}
              <h3 className="mt-5 font-display text-xl">Type on Paper</h3>
              {Object.entries(data.type_on_paper).map(([key, value]) => <p key={key} className="text-sm"><b>{key.replaceAll("_", " ")}:</b> {value ? String(value) : "???"}</p>)}
              <h3 className="mt-5 font-display text-xl">Recent memories</h3>
              {data.memories.length ? data.memories.map((m) => <p key={`${m.subject_id}-${m.formed_on_turn}`} className="mt-2 text-sm text-[var(--muted)]">{m.content}</p>) : <p className="text-sm text-[var(--muted)]">No memories yet.</p>}
            </>
          ) : <p>Loading...</p>}
          <button ref={closeRef} onClick={onClose} className="mt-6 rounded bg-accent px-4 py-2 text-[var(--card)]">Close</button>
        </section>
      </div>
    </div>
  );
}
