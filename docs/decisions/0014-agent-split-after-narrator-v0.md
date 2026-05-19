# 0014. Agent Split After Narrator v0

## Status

Accepted. Supersedes `0003-one-narrator-agent-for-v0.md` for the current POC.

## Context

The earliest implementation decision limited the POC to one Narrator agent until the deterministic loop was proven. The engine, CLI, scenario tests, FastAPI adapter, and browser client now exist. The codebase has separate typed wrappers for Islander Voice, Contextual Options, Event Narrator, Conversation Curator, Villa Orchestrator, and Background Dialogue.

## Decision

Keep the multi-agent split, but preserve the original boundary: agents narrate, propose typed options, summarize memories, and orchestrate NPC-facing intent. They do not mutate `GameState`, roll RNG, calculate success, choose eliminations, or advance phases.

Each agent surface must stay typed and mockable. Non-LLM tests use mock agents or recorded traces by default.

## Consequences

- Older docs that say "one Narrator only" are historical unless they refer to the initial build milestone.
- `ENGINEERING.md` R1, R2, R15, and R16 remain the authority for agent/engine separation.
- Adding a new agent requires a typed contract and tests around the engine boundary it touches.
