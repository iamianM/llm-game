import type { ApiMemory } from "../../lib/types";

export function MemoriesList({ memories }: { memories: ApiMemory[] }) {
  return (
    <section className="rounded-[var(--r-md)] border border-white/10 bg-white/5 p-3">
      <h3 className="font-display text-lg">Memories</h3>
      <div className="mt-3 space-y-2 text-sm text-[var(--muted-on-dark)]">
        {memories.length ? memories.map((memory) => <p key={`${memory.subject_id}-${memory.formed_on_turn}`}>{memory.content}</p>) : <p>No memories yet.</p>}
      </div>
    </section>
  );
}
