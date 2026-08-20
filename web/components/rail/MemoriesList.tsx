import type { ApiMemory } from "../../lib/types";

export function MemoriesList({ memories }: { memories: ApiMemory[] }) {
  const visibleMemories = memories.slice(0, 8);
  return (
    <section className="rail-section">
      <h3 className="rail-section-title">Memories</h3>
      <div className="memories">
        {visibleMemories.length ? (
          visibleMemories.map((memory, index) => (
            <p
              key={`${memory.id}-${memory.holder_id}-${memory.subject_id}-${memory.formed_on_turn}-${index}`}
              className="memory"
            >
              {memory.content}
            </p>
          ))
        ) : (
          <p className="empty">No memories yet.</p>
        )}
      </div>
      <style jsx>{`
        .rail-section {
          padding: 14px 14px 16px;
          border-radius: var(--r-lg);
          background: rgba(248,236,210,.04);
          border: 1px solid rgba(248,236,210,.08);
        }
        .rail-section-title {
          margin: 0 0 10px;
          font-size: 10px;
          letter-spacing: .16em;
          text-transform: uppercase;
          font-weight: 700;
          color: var(--gold-soft);
        }
        .memories { display: grid; gap: 8px; }
        .memory {
          margin: 0;
          font-size: 12.5px;
          line-height: 1.55;
          color: var(--muted-on-dark);
          padding-left: 10px;
          border-left: 2px solid rgba(217,167,58,.25);
          font-style: italic;
        }
        .empty {
          margin: 0;
          font-size: 12px;
          color: var(--muted-on-dark);
          opacity: .7;
        }
      `}</style>
    </section>
  );
}
