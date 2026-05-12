# 0003 - One Narrator Agent For v0

Date: 2026-05-11

## Context

The game design describes several possible AI roles: Producer, dialogue writer, event narrator, NPC behavior simulator, and memory curator. The steno runtime shows that multi-agent systems can work well when each role has a strict contract, but splitting roles too early adds complexity before the core loop is proven.

For the first playable version, deterministic Python can choose valid actions, calculate outcomes, move phases, and simulate NPC behavior.

## Decision

Start with one LLM agent: the Narrator.

The Narrator receives a fully resolved `MechanicalResult` plus visible scene context and returns prose/dialogue through one validated tool.

## Consequences

- No Director, Producer, or Curator agent in v0.
- The LLM never decides whether an action succeeds, which stats change, who is eliminated, or which phase comes next.
- Future agents can be added when deterministic rules become too rigid, but they must commit typed intent through validated tools.
- Tests can cover most gameplay with `--mock-llm` or fixed narration.
