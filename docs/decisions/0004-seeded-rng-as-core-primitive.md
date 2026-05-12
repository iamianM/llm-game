# 0004 - Seeded RNG As Core Primitive

Date: 2026-05-11

## Context

The game is a seasonal social sandbox with roguelite structure. Reproducible runs are essential for debugging, balance testing, scenario tests, and replay. Every outcome that looks random must be reproducible from a seed and action sequence.

## Decision

All randomness flows through a single seeded RNG abstraction owned by the engine.

## Consequences

- No direct calls to ambient randomness in gameplay modules.
- `MechanicalResult` and turn traces record enough RNG metadata to reproduce outcomes.
- Scenario tests can run fixed seeds and compare deterministic state snapshots.
- Balance tests can simulate many seeds without LLM calls.
- LLM output is flavor only and does not affect deterministic replay.
