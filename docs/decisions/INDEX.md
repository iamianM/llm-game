# Architecture Decision Records

This folder records implementation decisions that should not be re-litigated in every AI session.

Use `template.md` for new ADRs. ADRs are append-only: if a decision changes, add a new numbered ADR that supersedes the old one instead of rewriting history.

## Index

- `0001-python-engine-over-typescript.md` - Python owns the canonical engine.
- `0002-vite-over-nextjs.md` - The browser client uses Vite, not Next.js.
- `0003-one-narrator-agent-for-v0.md` - v0 starts with one Narrator agent.
- `0004-seeded-rng-as-core-primitive.md` - All randomness flows through seeded RNG.
- `0005-structured-content-not-runtime-design-docs.md` - Runtime content is structured markdown, not the full design vault.
- `0006-mechanics-in-code-flavor-in-content.md` - Mechanics live in code; flavor lives in content.
- `0007-engine-before-content-before-agents.md` - Build order is deterministic engine, then content, then agents.
- `0008-snapshot-and-trace-architecture.md` - Snapshots and traces are first-class debugging artifacts.
- `0009-action-vocabulary-as-single-source.md` - `ActionKind` is the canonical action vocabulary.
- `0010-engineering-rules.md` - `ENGINEERING.md` defines non-negotiable implementation discipline.
- `0011-makefile-cli-split.md` - CLI owns operations; Makefile wraps common commands.
