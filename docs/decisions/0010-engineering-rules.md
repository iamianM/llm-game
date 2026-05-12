# 0010 - Engineering Rules

Date: 2026-05-11

## Context

The project needs steno-style implementation discipline: no dead code, no legacy shims, no silent fallbacks, no over-engineering, and strict boundaries between engine, content, and agents.

## Decision

Use `ENGINEERING.md` as the non-negotiable engineering rules document.

## Consequences

- AI assistants must read `AGENTS.md` and `ENGINEERING.md` before coding.
- Reviews should cite rule numbers when flagging architectural violations.
- ADRs explain decisions; `ENGINEERING.md` defines implementation discipline.
