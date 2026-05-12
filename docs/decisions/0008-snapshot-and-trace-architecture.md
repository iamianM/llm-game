# 0008 - Snapshot And Trace Architecture

Date: 2026-05-11

## Context

Debugging a deterministic social simulation requires restarting from exact moments and comparing outcomes across CLI, browser, and tests.

## Decision

Snapshots and traces are first-class architecture.

Snapshots persist `GameState`, RNG state, turn index, phase, schema version, and state hash. Traces record each turn's input hash, action, RNG rolls, mechanical result, narration, and output hash.

## Consequences

- Bugs can be reproduced from snapshot + action.
- Scenario tests can assert state hashes.
- Browser dev mode can expose the same hash and trace ids the CLI uses.
- During POC, incompatible schema changes may regenerate fixtures rather than migrate them.
