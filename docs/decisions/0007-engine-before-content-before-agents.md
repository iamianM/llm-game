# 0007 - Engine Before Content Before Agents

Date: 2026-05-11

## Context

The design vault is large enough to tempt premature content authoring or agent work. That would create a lot of markdown and prompt surface before the game has a reproducible core loop.

ADRs 0003, 0004, 0005, and 0006 establish that v0 should be deterministic, replayable, and code-owned.

## Decision

Build in this order:

1. Deterministic engine loop
2. Minimal runtime content stubs
3. CLI play and replay
4. Engine and scenario tests
5. Narrator agent
6. FastAPI and Vite browser client
7. Expanded content

## Consequences

- The first real implementation file should be the seeded RNG boundary.
- Do not author a large `content/` library before one day is playable.
- Do not add Producer, Curator, or LLM-driven NPC behavior before the Narrator proves useful.
- Browser work waits until the CLI exercises the same engine successfully.
