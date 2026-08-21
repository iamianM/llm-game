# 0016 - Game-Owned Turn Agent Set

Date: 2026-08-21

## Context

`run_turn` exposes six optional agent callables. HTTP, CLI, eval, replay, report, and scenario callers repeat the roster and its mode-selection rules. The game eval module also imports the bundle from the HTTP adapter. Current fallback code silently substitutes deterministic mock output after live-agent failure, which contradicts `ENGINEERING.md` and decision 0014.

## Decision

Pass one canonical frozen turn-agent set through the `run_turn` seam. The set contains the six callable ports used during a turn. NPC greeting and trait generation remain session-setup concerns. The game owns the turn-agent set and its live, mock, recorded, and scripted adapters. Every caller selects an adapter explicitly and passes it intact.

Every port is callable. `None` is not a capability mode. The live adapter may expose named profiles such as `full` and `no_resort_life`, but each profile supplies all six ports. Contextual options use one exact five-argument port that includes `already_present`; callers and adapters do not inspect signatures at runtime.

Live agents fail the turn when they exhaust validation retries. Deterministic mock output exists only in explicit mock, recorded, or scripted adapters. The turn continues to own trace capture for its full lifetime.

A failed turn changes neither game state nor RNG state. Turn execution commits both together only after every required step succeeds.

The API reports an exhausted live-agent failure as a structured `STORY_ENGINE_ERROR` while retaining server-side traces. The CLI reports the failed turn and preserves the playable session. Evals record the failed turn and its traces. No surface substitutes mock prose.

Canonical trace capture remains in `run_turn`; adapter-specific attempt traces remain inside adapters. The unused async turn wrapper is deleted. Agent-set lifetime remains one set per CLI run, eval scenario, or API request rather than a process-wide singleton.

Implementation starts with a small contract-first seed change. The agent worktree then owns the frozen set, its four adapters, `run_turn` migration, failure propagation, and atomic rollback. Targeted interface, adapter, and caller tests run there. The integrated branch runs deterministic tests, mock golden evals, and the full `make qa` gate. Billed real-agent or judge checks run only if separately requested after the integrated change is otherwise ready.

## Consequences

- Callers stop learning and forwarding the six-agent roster.
- Live sessions cannot silently become mock sessions.
- Existing fallback tests must become strict failure-propagation tests.
- Every `run_turn` caller must select an adapter during migration.
- Turn execution needs an atomic state and RNG commit.
- Replay, deterministic scenarios, and golden evals must preserve their current hashes and recorded behavior.
- The LLM architecture and current plan must describe the verified adapter and failure contracts in present tense after implementation.
