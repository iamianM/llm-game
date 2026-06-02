export function ResortMap({ snapshot }: { snapshot: Record<string, string[]> }) {
  return (
    <section className="rail-section">
      <h3 className="rail-section-title">Where everyone is</h3>
      <div className="loc-grid">
        {Object.entries(snapshot).map(([location, names]) => {
          const occupied = names && names.length > 0;
          const youHere = (names ?? []).some((name) => name.toLowerCase() === "you");
          return (
            <div key={location} className={`loc-cell ${occupied ? "occupied" : "empty"} ${youHere ? "you-here" : ""}`}>
              <div className="loc-name">{location}</div>
              <div className="loc-names">
                {occupied ? (names ?? []).join(", ") : <span className="empty-label">—</span>}
              </div>
            </div>
          );
        })}
      </div>
      <style jsx>{`
        .rail-section {
          padding: 14px 14px 16px;
          border-radius: var(--r-lg);
          background: rgba(248,236,210,.04);
          border: 1px solid rgba(248,236,210,.08);
        }
        .rail-section-title {
          margin: 0 0 12px;
          font-size: 10px;
          letter-spacing: .16em;
          text-transform: uppercase;
          font-weight: 700;
          color: var(--gold-soft);
        }
        .loc-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 6px;
        }
        .loc-cell {
          padding: 8px 10px;
          border-radius: var(--r-md);
          background: rgba(8,6,4,.5);
          border: 1px solid rgba(248,236,210,.08);
          transition: border-color .2s, background .2s;
        }
        .loc-cell.empty .loc-names { color: var(--muted-on-dark); opacity: .4; }
        .loc-cell.you-here {
          border-color: rgba(217,167,58,.55);
          background: linear-gradient(180deg, rgba(217,167,58,.12), rgba(217,167,58,.04));
        }
        .loc-name {
          font-size: 10px;
          letter-spacing: .12em;
          text-transform: uppercase;
          font-weight: 700;
          color: var(--muted-on-dark);
          margin-bottom: 4px;
        }
        .loc-cell.you-here .loc-name { color: var(--gold-soft); }
        .loc-names {
          font-size: 12px;
          color: var(--ink-on-dark);
          line-height: 1.4;
        }
        .empty-label { opacity: .5; }
      `}</style>
    </section>
  );
}
