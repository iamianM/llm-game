# 0009 - Action Vocabulary As Single Source

Date: 2026-05-11

## Context

The same player action must mean the same thing in the browser, CLI, tests, and traces.

## Decision

`ActionKind` in `src/game/engine/actions.py` is the canonical action vocabulary.

The browser, CLI menus, scenario YAML, and tests reference action kinds from this vocabulary. New actions start in the engine and only then get UI or content flavor.

## Consequences

- No browser-only or CLI-only gameplay actions.
- Scenario scripts remain stable and machine-readable.
- Generated TypeScript types can mirror the canonical Python schema.
- Renaming an action requires updating fixtures and content lint.
