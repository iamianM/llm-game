# 0013. Typed Balance Data Boundary

## Status

Accepted. Refines `0005-structured-content-not-runtime-design-docs.md` and `0006-mechanics-in-code-flavor-in-content.md`.

## Context

The repo had two useful but conflicting rules:

- Runtime `content/` should be small, structured, and narrator-facing.
- Mechanics should live in Python, while content should carry flavor.

Intent tuning had grown into `content/intents.yaml`, and challenge markdown contained stat tests and relationship deltas even though Python also resolved challenge mechanics. That made `content/` both flavor source and mechanical source.

## Decision

Keep `content/` flavor-only. Markdown content may carry identifiers, display labels, ordering metadata, and narrator-facing prose, but it must not encode state mutation, scoring, unlocks, or deterministic branching.

Allow typed mechanical balance tables under `data/balance/`. These files may contain thresholds, deltas, weights, and other tunable numbers only when:

- Pydantic models validate the file shape.
- Python engine code is the only interpreter of the data.
- Tests protect the invariant the data affects.
- There is one source of truth for each mechanic.

## Consequences

- Conversation intent tuning lives in `data/balance/intents.yaml`.
- Challenge markdown no longer carries stat tests or deltas; challenge mechanics stay in `src/game/engine/challenges.py` until a dedicated balance table is worth adding.
- Content lint may validate balance references, but should name them as balance data rather than runtime flavor content.
- This does not permit free-form logic or formulas in YAML. Declarative data is allowed; gameplay behavior remains code-owned.
