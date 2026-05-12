# 0011 - Makefile And CLI Split

Date: 2026-05-11

## Context

The project needs both fast human commands and a structured tool surface for AI agents, tests, and debugging.

## Decision

The CLI is the program surface. The Makefile is only a shortcut layer.

Real operations live as `python -m src.game.cli ...` subcommands. Make targets wrap those commands and never duplicate business logic.

## Consequences

- CLI subcommands are importable and testable.
- Windows users can use the CLI even without `make`.
- AI agents should prefer explicit CLI commands when debugging.
- Make stays small and focused on common workflows like `make qa`.
