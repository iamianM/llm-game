# 0014. Agent Split After Narrator v0

## Status

Accepted. Supersedes `0003-one-narrator-agent-for-v0.md` for the current POC.

## Context

The earliest implementation decision limited the POC to one Narrator agent until the deterministic loop was proven. The engine, CLI, scenario tests, FastAPI adapter, and browser client now exist. The codebase has separate typed wrappers for Islander Voice, Contextual Options, Event Narrator, Conversation Curator, Villa Orchestrator, and Background Dialogue.

## Decision

Keep the multi-agent split, but preserve the original boundary: agents narrate, propose typed options, summarize memories, and orchestrate NPC-facing intent. They do not mutate `GameState`, roll RNG, calculate success, choose eliminations, or advance phases.

Each agent surface must stay typed and mockable. Non-LLM tests use mock agents or recorded traces by default.

Agent context may include visible, engine-owned setup facts that the model must
respond to, such as a successful pull for chat, pending proposal, or resolved
event. Those facts are passed as structured context from `MechanicalResult` or
canonical state; they are not agent decisions and they must not be inferred from
free-text history when the engine already knows them.

Real agent calls must request structured output through the typed contract when
the provider supports it, validate the parsed Pydantic model, and retry only
with explicit validation feedback. If the contract still fails, the call fails
loudly at the adapter boundary; it must not substitute a heuristic fallback or
repair the response with string matching.

When a contract intentionally uses dynamic object keys that the provider's
strict schema subset cannot represent, the wrapper may request JSON-object mode
and immediately parse it through the same Pydantic contract. This is still a
typed agent boundary; the provider is not trusted to repair, coerce, or score
the result.

## Consequences

- Older docs that say "one Narrator only" are historical unless they refer to the initial build milestone.
- `ENGINEERING.md` R1, R2, R15, and R16 remain the authority for agent/engine separation.
- Adding a new agent requires a typed contract and tests around the engine boundary it touches.
