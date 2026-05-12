# 0006 - Mechanics In Code, Flavor In Content

Date: 2026-05-11

## Context

Actions, events, and challenges contain both mechanical behavior and narrative flavor. Putting too much behavior in markdown frontmatter would create an untyped rules language that is harder to test than Python.

## Decision

Use Python for anything that changes state or has branching/math. Use markdown content for prose, tone, and light metadata.

## Consequences

- Action mechanics live in `src/game/engine/actions.py` and related modules.
- Event and challenge mechanics live in engine modules.
- Optional `content/actions/`, `content/events/`, and `content/challenges/` files provide narrator-facing flavor only.
- `content_lint` validates frontmatter ids against engine enums and Pydantic models.
- Design docs are cited in module docstrings and tests, keeping the implementation tied to the canon without making prose executable.
