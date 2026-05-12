# 0005 - Structured Content, Not Runtime Design Docs

Date: 2026-05-11

## Context

The repository has substantial design documentation. Those docs should remain core to implementation, but feeding long design prose into the engine or Narrator every turn would be expensive, noisy, and hard to validate.

The useful pattern from steno is authored markdown with frontmatter loaded into Pydantic models, not runtime ingestion of broad design documents.

## Decision

Keep the current design docs as design canon. Create smaller runtime content files for narrator-relevant prose and light metadata.

## Consequences

- `00-*.md` through `12-*.md` remain high-level design references.
- Runtime-loaded content lives under `content/` and is validated by `src/game/content/`.
- Mechanics, branching, math, and state changes live in Python code.
- Markdown content may provide archetype flavor, location mood, display copy, and event beats.
- The Narrator receives only relevant snippets, never the full design vault.
