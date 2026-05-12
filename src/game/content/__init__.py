"""Runtime-loaded markdown content.

Design sources:
- docs/decisions/0005-structured-content-not-runtime-design-docs.md
- docs/decisions/0006-mechanics-in-code-flavor-in-content.md

Implementation rule:
Content carries prose and light metadata. Mechanics, branching, math, and state
changes live in `src/game/engine/`.
"""
